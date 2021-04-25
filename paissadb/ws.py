import asyncio
import logging

from broadcaster import Broadcast
from fastapi import WebSocket
from sqlalchemy.orm import Session
from websockets import ConnectionClosed

from . import calc, config, crud, models, schemas

CHANNEL = "messages"
log = logging.getLogger(__name__)

manager = Broadcast(config.WS_BACKEND_URI)
broadcast_queue = asyncio.Queue()  # maybe eventually this should be redis, and we can remove the manager


# hierarchy summary:
# broadcast_* is the main entrypoint (sync)
# it pushes messages to the broadcast queue
# all messages in the broadcast queue are eventually sent to the manager
# all messages in the manager (regardless of origin process) are eventually sent to all connected websockets


# ==== lifecycle ====
async def broadcast_loop():
    """Main loop of the ws module - broadcasts all messages put to *broadcast_queue*."""
    while True:
        try:
            msg = await broadcast_queue.get()
            await manager.publish(CHANNEL, msg)
        except asyncio.CancelledError:
            pass


async def connect(websocket: WebSocket):
    """Accepts the websocket connection and sets up its ping and broadcast listeners."""
    await websocket.accept()
    task = asyncio.gather(
        ping(websocket),
        listener(websocket)
    )
    try:
        await task
    except ConnectionClosed as e:
        print(f"WS disconnected ({e.code}: {e.reason}): {websocket.client!r}")
        task.cancel()


# ==== tasks ====
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


# ==== broadcasts ====
def broadcast_changes_in_wardsweep(db: Session, wardsweep: models.WardSweep):
    plot_history = crud.get_plot_states_before(
        db, wardsweep.world_id, wardsweep.territory_type_id, wardsweep.ward_number, wardsweep.timestamp)
    history_map = {p.plot_number: p for p in plot_history}
    for plot in wardsweep.plots:
        before = history_map.get(plot.plot_number)
        # seen for first time, and is open
        if before is None and not plot.is_owned:
            broadcast_plot_open(db, plot)
        # owned -> open
        elif before is not None and before.is_owned and not plot.is_owned:
            broadcast_plot_open(db, plot)
        # open -> sold
        elif before is not None and not before.is_owned and plot.is_owned:
            broadcast_plot_sold(db, plot)


def broadcast_plot_open(db: Session, plot: models.Plot):
    detail = calc.open_plot_detail(db, plot)
    data = schemas.paissa.WSPlotOpened(data=detail)
    broadcast_queue.put_nowait(data.json())


def broadcast_plot_sold(db: Session, plot: models.Plot):
    detail = calc.sold_plot_detail(db, plot)
    data = schemas.paissa.WSPlotSold(data=detail)
    broadcast_queue.put_nowait(data.json())
