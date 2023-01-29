import asyncio
import logging
import time
from typing import List, Optional

from fastapi import WebSocket
from sqlalchemy.orm import Session
from websockets import ConnectionClosed

from common import crud, schemas, utils
from common.database import PUBSUB_WS_CHANNEL, redis

log = logging.getLogger(__name__)

ONE_DAY = 60 * 60 * 24
pubsub = redis.pubsub()


class WebsocketClient:
    def __init__(self, conn: WebSocket, anonymous: bool):
        self.conn = conn
        self.anonymous = anonymous
        self.connected_at = time.time()

    async def send_text(self, data: str):
        await self.conn.send_text(data)

    async def close(self, code=1000):
        return await self.conn.close(code)


clients: List[WebsocketClient] = []


async def connect(db: Session, websocket: WebSocket, user: Optional[schemas.paissa.JWTSweeper]):
    """Accepts the websocket connection and sets up its ping and broadcast listeners."""
    await websocket.accept()
    if user is not None:
        await utils.executor(crud.touch_sweeper_by_id, db, user.cid)
    client = WebsocketClient(websocket, user is not None)
    clients.append(client)
    try:
        await ping(client, delay=90)
    finally:
        clients.remove(client)


async def ping(websocket: WebsocketClient, delay=60):
    """Naively sends a ping message to the given websocket every 60 seconds."""
    while True:
        try:
            await websocket.send_text('{"type": "ping"}')  # save a bit of time by having this pre-serialized
            await asyncio.sleep(delay)
            # disconnect anonymous clients who have been connected for >24h
            if websocket.anonymous and time.time() - websocket.connected_at > ONE_DAY:
                log.info(f"WS disconnect anonymous >1d: {websocket.conn.client!r}")
                await websocket.close()
                return
        except ConnectionClosed as e:
            log.info(f"WS disconnected ({e.code}: {e.reason}): {websocket.conn.client!r}")
            return
        except asyncio.CancelledError:
            return


async def broadcast_listener():
    """Sends all messages received over the broadcast manager to all connected websockets."""
    await pubsub.subscribe(PUBSUB_WS_CHANNEL)
    while True:
        try:
            message = pubsub.handle_message(await pubsub.parse_response(block=True), ignore_subscribe_messages=True)
            if message is None:
                continue
            data = message["data"]
            # we do this instead of iterating over the clients for concurrency and so the clients list cannot
            # change during our iteration
            # we don't care about bad connections here, the ping will clean those up
            asyncio.ensure_future(
                asyncio.gather(*(websocket.send_text(data) for websocket in clients), return_exceptions=True)
            )
        except asyncio.CancelledError:
            break
        except Exception:
            log.exception("Failed to broadcast received data:")
        finally:
            await asyncio.sleep(0.01)
