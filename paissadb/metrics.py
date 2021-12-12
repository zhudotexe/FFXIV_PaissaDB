"""
Prometheus metrics
"""
import asyncio
import logging
import uuid
from typing import Callable, Dict, TypeVar

from prometheus_client import Gauge
from prometheus_fastapi_instrumentator import Instrumentator

from common.database import EVENT_QUEUE_KEY, METRICS_KEY_PREFIX, redis
from . import ws

log = logging.getLogger(__name__)
_event_queue_size = 0
_num_ws_conns = 0

WORKER_ID = str(uuid.uuid4())  # random uuid for aggregate metrics
AGG_METRICS_REFRESH_TIME = 15

T = TypeVar("T")


# ==== tasks ====
async def metrics_task():
    """Updates various metrics every 15 seconds."""
    global _event_queue_size, _num_ws_conns  # :(
    while True:
        try:
            await _update_agg_metrics()
            _num_ws_conns = await _fetch_agg_metric("ws_conns", strategy=sum_values)
            _event_queue_size = await redis.zcard(EVENT_QUEUE_KEY)
        except asyncio.CancelledError:
            break
        except Exception:
            log.exception("Failed to update event queue size:")
        finally:
            await asyncio.sleep(AGG_METRICS_REFRESH_TIME)


async def _update_agg_metrics():
    """Writes this worker's portion of the agg metrics to redis"""
    await redis.set(
        f"{METRICS_KEY_PREFIX}:ws_conns:{WORKER_ID}",
        len(ws.clients),
        ex=AGG_METRICS_REFRESH_TIME + 1
    )
    await redis.sadd(f"{METRICS_KEY_PREFIX}:members", WORKER_ID)


async def _fetch_agg_metric(metric: str, strategy: Callable[[Dict[str, str]], T] = lambda d: d) -> T:
    """
    Fetch a mapping of worker id to last posted metric for a given agg metric.
    If a worker is found in the worker members set but does not have a valid entry for the agg metric, the worker
    is removed from the worker members set.
    """
    members = await redis.smembers(f"{METRICS_KEY_PREFIX}:members")
    data = {}
    for member_id in members:
        member_data = await redis.get(f"{METRICS_KEY_PREFIX}:{metric}:{member_id}")
        if member_data is None:
            await redis.srem(f"{METRICS_KEY_PREFIX}:members", member_id)
        else:
            data[member_id] = member_data
    return strategy(data)


# ==== prom ====
def register(app):
    """Registers and exposes instrumentation on the given FastAPI instance."""
    Instrumentator().instrument(app).expose(app, include_in_schema=False)


event_qsize = Gauge('event_qsize', 'The size of the event processing queue')
event_qsize.set_function(lambda: _event_queue_size)

ws_conns = Gauge('ws_conns', 'The number of clients connected to the websocket')
ws_conns.set_function(lambda: _num_ws_conns)


# ==== helpers ====
def sum_values(data: Dict[str, str]) -> int:
    """Sum the values of a dict."""
    return sum(map(int, data.values()))
