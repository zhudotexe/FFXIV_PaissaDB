import asyncio
import logging
import sys
from typing import List, Optional

import jwt as jwtlib  # name conflict with jwt query param in /ws
import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sqlalchemy.orm import Session

from common import config, gamedata, models, schemas, utils
from common.database import SessionLocal, engine, get_db
from . import auth, calc, crud, metrics, ws

# todo move this to the worker
models.Base.metadata.create_all(bind=engine)
with SessionLocal() as sess:
    gamedata.upsert_all(gamedata_dir=config.GAMEDATA_DIR, db=sess)

log = logging.getLogger(__name__)
if 'debug' in sys.argv:
    # noinspection PyArgumentList
    logging.basicConfig(stream=sys.stdout, encoding='utf-8', level=logging.DEBUG)

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
@app.post("/wardInfo", status_code=202)
async def ingest_wardinfo(
    wardinfo: schemas.ffxiv.HousingWardInfo,
    sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
    db: Session = Depends(get_db)
):
    """Legacy single-ward ingest endpoint - use /ingest instead"""
    return await bulk_ingest([wardinfo], sweeper, db)


@app.post("/ingest", status_code=202)
async def bulk_ingest(
    data: List[schemas.ffxiv.BaseFFXIVPacket],
    sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
    db: Session = Depends(get_db)
):
    await crud.bulk_ingest(db, data, sweeper)
    await utils.executor(crud.touch_sweeper_by_id, db, sweeper.cid)
    return {"message": "OK", "accepted": len(data)}


@app.post("/hello")
def hello(
    data: schemas.paissa.Hello,
    sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
    db: Session = Depends(get_db)
):
    if sweeper.cid != data.cid:
        raise HTTPException(400, "Token CID and given CID do not match")
    log.debug("Received hello:")
    log.debug(data.json())
    crud.upsert_sweeper(db, data)
    crud.touch_sweeper_by_id(db, sweeper.cid)
    return {"message": "OK"}


@app.get("/worlds", response_model=List[schemas.paissa.WorldSummary])
def list_worlds(db: Session = Depends(get_db)):
    worlds = crud.get_worlds(db)
    out = []
    for world in worlds:
        out.append(schemas.paissa.WorldSummary(id=world.id, name=world.name))
    return out


@app.get("/worlds/{world_id}", response_model=schemas.paissa.WorldDetail)
def get_world(world_id: int, db: Session = Depends(get_db)):
    world = crud.get_world_by_id(db, world_id)
    districts = crud.get_districts(db)
    if world is None:
        raise HTTPException(404, "World not found")

    district_details = []
    for district in districts:
        district_details.append(calc.get_district_detail(db, world, district))

    return schemas.paissa.WorldDetail(
        id=world.id,
        name=world.name,
        districts=district_details,
        num_open_plots=sum(d.num_open_plots for d in district_details),
        oldest_plot_time=min(d.oldest_plot_time for d in district_details)
    )


@app.get("/worlds/{world_id}/{district_id}", response_model=schemas.paissa.DistrictDetail)
def get_district_detail(world_id: int, district_id: int, db: Session = Depends(get_db)):
    world = crud.get_world_by_id(db, world_id)
    district = crud.get_district_by_id(db, district_id)
    if world is None or district is None:
        raise HTTPException(404, "World not found")

    return calc.get_district_detail(db, world, district)


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
    asyncio.create_task(metrics.event_queue_task())


@app.on_event("shutdown")
async def on_shutdown():
    for client in ws.clients:
        await client.close(status.WS_1012_SERVICE_RESTART)
