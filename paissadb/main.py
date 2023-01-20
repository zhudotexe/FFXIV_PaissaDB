import asyncio
import csv
import io
import logging
import sys
import time
from typing import List, Optional

import jwt as jwtlib  # name conflict with jwt query param in /ws
import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sqlalchemy.orm import Session

from common import calc, config, crud, schemas
from common.database import get_db
from . import auth, metrics, ws

log = logging.getLogger(__name__)
if "debug" in sys.argv:
    # noinspection PyArgumentList
    logging.basicConfig(stream=sys.stdout, encoding="utf-8", level=logging.DEBUG)

app = FastAPI()

# ==== Middleware ====
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Sentry
if config.SENTRY_DSN is not None:
    sentry_sdk.init(dsn=config.SENTRY_DSN, environment=config.SENTRY_ENV, integrations=[SqlalchemyIntegration()])
    app.add_middleware(SentryAsgiMiddleware)
# Prometheus
metrics.register(app)


# ==== HTTP ====
# --- ingest ---
@app.post("/ingest", status_code=202)
async def bulk_ingest(
    data: List[schemas.ffxiv.BaseFFXIVPacket],
    sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
    db: Session = Depends(get_db),
):
    await crud.bulk_ingest(db, data, sweeper)
    return {"message": "OK", "accepted": len(data)}


@app.post("/hello")
def hello(
    data: schemas.paissa.Hello,
    # sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
    db: Session = Depends(get_db),
):
    # if sweeper.cid != data.cid:
    #     raise HTTPException(400, "Token CID and given CID do not match")
    log.debug("Received hello:")
    log.debug(data.json())
    session_token = auth.create_session_token(data)
    crud.upsert_sweeper(db, data)
    crud.touch_sweeper_by_id(db, data.cid)
    return {"message": "OK", "server_time": time.time(), "session_token": session_token}


# --- API ---
@app.get("/worlds", response_model=List[schemas.paissa.WorldSummary])
def list_worlds(db: Session = Depends(get_db)):
    worlds = crud.get_worlds(db)
    out = []
    for world in worlds:
        out.append(
            schemas.paissa.WorldSummary(
                id=world.id, name=world.name, datacenter_id=world.datacenter_id, datacenter_name=world.datacenter_name
            )
        )
    return out


@app.get("/worlds/{world_id}", response_model=schemas.paissa.WorldDetail)
def get_world(world_id: int, db: Session = Depends(get_db)):
    world = crud.get_world_by_id(db, world_id)
    if world is None:
        raise HTTPException(404, "World not found")

    return calc.get_district_detail(db, world)


@app.get("/worlds/{world_id}/{district_id}", response_model=schemas.paissa.DistrictDetail)
def get_district_detail(world_id: int, district_id: int, db: Session = Depends(get_db)):
    world = crud.get_world_by_id(db, world_id)
    district = crud.get_district_by_id(db, district_id)
    if world is None or district is None:
        raise HTTPException(404, "World not found")

    return calc.get_district_detail(db, world, district)


# --- CSV export ---
@app.get("/csv/entries")
def get_entries_csv(db: Session = Depends(get_db)):
    """
    Exports the entry stats from the most recent complete entry cycle, ordered by entry count descending.
    """
    csvbuf = io.StringIO()

    writer = csv.DictWriter(
        csvbuf, fieldnames=("world", "district", "ward_number", "plot_number", "house_size", "lotto_entries", "price")
    )
    writer.writeheader()
    for row in crud.last_entry_cycle_entries(db):
        writer.writerow(row._asdict())

    csvbuf.seek(0)
    response = StreamingResponse(
        csvbuf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )
    return response


# --- misc ---
@app.get("/")
async def root():
    return RedirectResponse("https://zhu.codes/paissa")


# ==== WS ====
@app.websocket("/ws")
async def plot_updates(websocket: WebSocket, jwt: Optional[str] = None, db: Session = Depends(get_db)):
    if jwt is None:
        await ws.connect(db, websocket, None)
        return

    # if token is present, it must be valid
    try:
        sweeper = auth.decode_token(jwt)
    except jwtlib.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws.connect(db, websocket, sweeper)


# ==== lifecycle ====
@app.on_event("startup")
async def on_startup():
    # this never gets cancelled explicitly, it's just killed when the app dies
    asyncio.create_task(ws.broadcast_listener())
    asyncio.create_task(metrics.metrics_task())


@app.on_event("shutdown")
async def on_shutdown():
    await asyncio.gather(
        *[client.close(status.WS_1012_SERVICE_RESTART) for client in ws.clients], return_exceptions=True
    )
