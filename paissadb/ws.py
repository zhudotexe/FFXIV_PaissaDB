import asyncio
import logging
import multiprocessing
from typing import List, Optional

from fastapi import WebSocket
from sqlalchemy.orm import Session
from websockets import ConnectionClosed

from . import calc, crud, models, schemas, utils
from .database import SessionLocal, redis

CHANNEL = "messages"
log = logging.getLogger(__name__)

pubsub = redis.pubsub()
clients: List[WebSocket] = []
broadcast_process_queue = multiprocessing.Queue()


# ==== lifecycle ====
async def connect(db: Session, websocket: WebSocket, user: Optional[schemas.paissa.JWTSweeper]):
    """Accepts the websocket connection and sets up its ping and broadcast listeners."""
    await websocket.accept()
    if user is not None:
        await utils.executor(crud.touch_sweeper_by_id, db, user.cid)
    clients.append(websocket)
    try:
        await ping(websocket)
    finally:
        clients.remove(websocket)


# ==== websocket tasks ====
async def ping(websocket: WebSocket, delay=60):
    """Naively sends a ping message to the given websocket every 60 seconds."""
    while True:
        try:
            await websocket.send_text('{"type": "ping"}')  # save a bit of time by having this pre-serialized
            await asyncio.sleep(delay)
        except ConnectionClosed as e:
            log.info(f"WS disconnected ({e.code}: {e.reason}): {websocket.client!r}")
            return
        except asyncio.CancelledError:
            return


# ==== processing tasks ====
async def queue_wardsweep_for_processing(wardsweep: models.WardSweep):
    broadcast_process_queue.put(wardsweep.id, block=False)


async def broadcast_listener():
    """Sends all messages received over the broadcast manager to all connected websockets."""
    await pubsub.subscribe(CHANNEL)
    while True:
        try:
            message = pubsub.handle_message(
                await pubsub.parse_response(block=True),
                ignore_subscribe_messages=True
            )
            if message is None:
                continue
            data = message['data'].decode()
            # we do this instead of iterating over the clients for concurrency and so the clients list cannot
            # change during our iteration
            # we don't care about bad connections here, the ping will clean those up
            await asyncio.gather(*(websocket.send_text(data) for websocket in clients), return_exceptions=True)
        except asyncio.CancelledError:
            break
        except Exception:
            log.exception("Failed to broadcast received data:")
        finally:
            await asyncio.sleep(0.01)


# ==== multiprocessing entrypoint ====
def sweep_processer_entrypoint():
    asyncio.run(process_wardsweeps())


async def process_wardsweeps():
    while True:
        try:
            sweep_id = broadcast_process_queue.get(block=True)
            with SessionLocal() as db:
                wardsweep = await utils.executor(crud.get_wardsweep_by_id, db, sweep_id)
                await broadcast_changes_in_wardsweep(db, wardsweep)
        except (asyncio.CancelledError, KeyboardInterrupt):
            break
        except Exception:
            log.exception("Failed to process wardsweep:")
        finally:
            # small delay to prevent task from hogging system resources
            await asyncio.sleep(0.05)


async def broadcast(message: str):
    await redis.publish(CHANNEL, message)


async def broadcast_changes_in_wardsweep(db: Session, wardsweep: models.WardSweep):
    plot_history = await utils.executor(
        crud.get_plot_states_before,
        db, wardsweep.world_id, wardsweep.territory_type_id, wardsweep.ward_number, wardsweep.timestamp
    )
    history_map = {p.plot_number: p for p in plot_history}
    for plot in wardsweep.plots:
        before = history_map.get(plot.plot_number)
        # seen for first time, and is open
        if before is None and not plot.is_owned:
            await broadcast_plot_open(db, plot)
        # owned -> open
        elif before is not None and before.is_owned and not plot.is_owned:
            await broadcast_plot_open(db, plot)
        # open -> sold
        elif before is not None and not before.is_owned and plot.is_owned:
            await broadcast_plot_sold(db, plot)


async def broadcast_plot_open(db: Session, plot: models.Plot):
    detail = await utils.executor(calc.open_plot_detail, db, plot)
    data = schemas.paissa.WSPlotOpened(data=detail)
    await broadcast(data.json())


async def broadcast_plot_sold(db: Session, plot: models.Plot):
    detail = await utils.executor(calc.sold_plot_detail, db, plot)
    data = schemas.paissa.WSPlotSold(data=detail)
    await broadcast(data.json())
