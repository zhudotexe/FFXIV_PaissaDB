"""
Prometheus metrics
"""
from prometheus_client import Gauge
from prometheus_fastapi_instrumentator import Instrumentator

from . import ws


def register(app):
    """Registers and exposes instrumentation on the given FastAPI instance."""
    Instrumentator().instrument(app).expose(app, include_in_schema=False)


wardsweep_qsize = Gauge('wardsweep_qsize', 'The size of the wardsweep processing queue')
wardsweep_qsize.set_function(lambda: ws.broadcast_process_queue.qsize())

ws_conns = Gauge('ws_conns', 'The number of clients connected to the websocket')
ws_conns.set_function(lambda: len(ws.clients))
