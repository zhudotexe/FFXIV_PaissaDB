"""
Prometheus metrics
"""
import asyncio
import logging

from prometheus_client import Gauge
from prometheus_fastapi_instrumentator import Instrumentator

from common.database import EVENT_QUEUE_KEY, redis
from . import ws

log = logging.getLogger(__name__)
_event_queue_size = 0


def register(app):
    """Registers and exposes instrumentation on the given FastAPI instance."""
    Instrumentator().instrument(app).expose(app, include_in_schema=False)


async def event_queue_task():
    """Update the event queue size every 15 seconds."""
    global _event_queue_size  # :(
    while True:
        try:
            _event_queue_size = await redis.zcard(EVENT_QUEUE_KEY)
        except asyncio.CancelledError:
            break
        except Exception:
            log.exception("Failed to update event queue size:")
        finally:
            await asyncio.sleep(15)


event_qsize = Gauge('event_qsize', 'The size of the event processing queue')
event_qsize.set_function(lambda: _event_queue_size)

ws_conns = Gauge('ws_conns', 'The number of clients connected to the websocket')
ws_conns.set_function(lambda: len(ws.clients))
