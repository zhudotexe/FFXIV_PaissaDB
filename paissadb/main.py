import asyncio
import datetime
import logging
import sys
from typing import List, Optional

import jwt as jwtlib  # name conflict with jwt query param in /ws
import sentry_sdk
import sqlalchemy.exc
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sqlalchemy.orm import Session

from . import auth, calc, config, crud, gamedata, metrics, models, schemas, ws
from .database import SessionLocal, engine, get_db

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
def ingest_wardinfo(
        wardinfo: schemas.ffxiv.HousingWardInfo,
        background: BackgroundTasks,
        sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
        db: Session = Depends(get_db)):
    log.debug("Received wardInfo:")
    log.debug(wardinfo.json())

    try:
        wardsweep = crud.ingest_wardinfo(db, wardinfo, sweeper)
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        try:
            wardsweep = crud.ingest_wardinfo(db, wardinfo, None)
        except sqlalchemy.exc.IntegrityError:
            raise HTTPException(400, "Could not ingest sweep")

    db.close()
    background.add_task(ws.queue_wardsweep_for_processing, wardsweep)
    return {"message": "OK"}


@app.post("/hello")
def hello(
        data: schemas.paissa.Hello,
        sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
        db: Session = Depends(get_db)):
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
    districts = crud.get_districts(db)

    out = []
    for world in worlds:
        district_summaries = []
        for district in districts:
            latest_plots = crud.get_latest_plots_in_district(db, world.id, district.id, use_cache=True)
            num_open_plots = sum(1 for p in latest_plots if not p.is_owned)
            oldest_plot_time = min(p.timestamp for p in latest_plots) \
                if latest_plots else datetime.datetime.fromtimestamp(0)
            district_summaries.append(schemas.paissa.DistrictSummary(
                id=district.id,
                name=district.name,
                num_open_plots=num_open_plots,
                oldest_plot_time=oldest_plot_time
            ))
        out.append(schemas.paissa.WorldSummary(
            id=world.id,
            name=world.name,
            districts=district_summaries,
            num_open_plots=sum(d.num_open_plots for d in district_summaries),
            oldest_plot_time=min(d.oldest_plot_time for d in district_summaries)
        ))
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
@app.on_event("startup")
async def connect_broadcast():
    await ws.manager.connect()
    # this never gets cancelled explicitly, it's just killed when the app dies
    asyncio.create_task(ws.process_wardsweeps())


@app.on_event("shutdown")
async def disconnect_broadcast():
    for client in ws.clients:
        await client.close(status.WS_1012_SERVICE_RESTART)
    await ws.manager.disconnect()


@app.websocket("/ws")
async def plot_updates(websocket: WebSocket, jwt: Optional[str] = None, db: Session = Depends(get_db)):
    # token must be present
    if jwt is None:
        await ws.connect(db, websocket, None)  # fixme
        # await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # and valid
    try:
        sweeper = auth.decode_token(jwt)
    except jwtlib.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws.connect(db, websocket, sweeper)
