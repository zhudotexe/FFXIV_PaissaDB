import asyncio
import logging
from typing import List, Optional

from broadcaster import Broadcast
from fastapi import WebSocket
from sqlalchemy.orm import Session
from websockets import ConnectionClosed

from . import calc, config, crud, models, schemas
from .database import SessionLocal

CHANNEL = "messages"
log = logging.getLogger(__name__)

manager = Broadcast(config.WS_BACKEND_URI)
clients: List[WebSocket] = []
broadcast_process_queue = asyncio.Queue()


# ==== lifecycle ====
async def connect(db: Session, websocket: WebSocket, user: Optional[schemas.paissa.JWTSweeper]):
    """Accepts the websocket connection and sets up its ping and broadcast listeners."""
    await websocket.accept()
    if user is not None:
        await asyncio.get_running_loop().run_in_executor(None, crud.touch_sweeper_by_id, db, user.cid)

    task = asyncio.gather(
        ping(websocket),
        listener(websocket)
    )
    try:
        clients.append(websocket)
        await task
    except ConnectionClosed as e:
        log.info(f"WS disconnected ({e.code}: {e.reason}): {websocket.client!r}")
        clients.remove(websocket)
        task.cancel()


# ==== websocket tasks ====
async def ping(websocket: WebSocket, delay=60):
    """Naively sends a ping message to the given websocket every 60 seconds."""
    while True:
        try:
            await websocket.send_text('{"type": "ping"}')  # save a bit of time by having this pre-serialized
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            break


async def listener(websocket: WebSocket):
    """Sends all messages received over the broadcast manager to the given websocket."""
    async with manager.subscribe(CHANNEL) as subscriber:
        async for event in subscriber:
            try:
                await websocket.send_text(event.message)
            except asyncio.CancelledError:
                break


# ==== processing tasks ====
async def queue_wardsweep_for_processing(wardsweep: models.WardSweep):
    await broadcast_process_queue.put(wardsweep.id)
    if (qsize := broadcast_process_queue.qsize()) > 50:
        log.warning(f"Broadcast process queue is getting large! ({qsize=})")


async def process_wardsweeps():
    while True:
        try:
            with SessionLocal() as db:
                sweep_id = await broadcast_process_queue.get()
                wardsweep = await asyncio.get_running_loop() \
                    .run_in_executor(None, crud.get_wardsweep_by_id, db, sweep_id)
                await broadcast_changes_in_wardsweep(db, wardsweep)
                qsize = broadcast_process_queue.qsize()
                if qsize > 50:
                    log.warning(f"Broadcast process queue is still large! ({qsize=})")
        except asyncio.CancelledError:
            break
        except Exception:
            log.exception("Failed to process wardsweep:")
        finally:
            # small delay to prevent task from hogging system resources
            # historically this processes at ~4.3/s (0.23s/per), so this limits it to roughly 3/s
            await asyncio.sleep(0.1)


# ==== broadcasts ====
async def broadcast(message: str):
    await manager.publish(CHANNEL, message)


async def broadcast_changes_in_wardsweep(db: Session, wardsweep: models.WardSweep):
    plot_history = await asyncio.get_running_loop().run_in_executor(
        None, crud.get_plot_states_before,
        db, wardsweep.world_id, wardsweep.territory_type_id, wardsweep.ward_number, wardsweep.timestamp)
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
    detail = calc.open_plot_detail(db, plot)
    data = schemas.paissa.WSPlotOpened(data=detail)
    await broadcast(data.json())


async def broadcast_plot_sold(db: Session, plot: models.Plot):
    detail = calc.sold_plot_detail(db, plot)
    data = schemas.paissa.WSPlotSold(data=detail)
    await broadcast(data.json())
