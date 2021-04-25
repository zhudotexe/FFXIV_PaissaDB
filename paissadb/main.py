import asyncio
import datetime
import logging
from typing import List

from fastapi import Depends, FastAPI, HTTPException, WebSocket
from sqlalchemy.orm import Session

from . import auth, calc, config, crud, gamedata, models, schemas, ws
from .database import SessionLocal, engine, get_db

models.Base.metadata.create_all(bind=engine)
with SessionLocal() as sess:
    gamedata.upsert_all(gamedata_dir=config.GAMEDATA_DIR, db=sess)

log = logging.getLogger(__name__)
app = FastAPI()


# ==== HTTP ====
@app.post("/wardInfo", status_code=201)
def ingest_wardinfo(
        wardinfo: schemas.ffxiv.HousingWardInfo,
        sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
        db: Session = Depends(get_db)):
    log.debug("Received wardInfo:")
    log.debug(wardinfo.json(indent=2))
    wardsweep = crud.ingest_wardinfo(db, wardinfo, sweeper)
    ws.broadcast_changes_in_wardsweep(db, wardsweep)
    return {"message": "OK"}


@app.post("/hello")
def hello(
        data: schemas.paissa.Hello,
        sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
        db: Session = Depends(get_db)):
    if sweeper.cid != data.cid:
        raise HTTPException(400, "Token CID and given CID do not match")
    log.debug("Received hello:")
    log.debug(data.json(indent=2))
    crud.upsert_sweeper(db, data)
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
        latest_plots = crud.get_latest_plots_in_district(db, world.id, district.id)
        num_open_plots = sum(1 for p in latest_plots if not p.is_owned)
        oldest_plot_time = min(p.timestamp for p in latest_plots) \
            if latest_plots else datetime.datetime.fromtimestamp(0)
        open_plots = []

        for plot in latest_plots:
            if plot.is_owned:
                continue
            # we found a plot that was last known as open, iterate over its history to find the details
            open_plots.append(calc.open_plot_detail(db, plot))

        district_details.append(schemas.paissa.DistrictDetail(
            id=district.id,
            name=district.name,
            num_open_plots=num_open_plots,
            oldest_plot_time=oldest_plot_time,
            open_plots=open_plots
        ))

    return schemas.paissa.WorldDetail(
        id=world.id,
        name=world.name,
        districts=district_details,
        num_open_plots=sum(d.num_open_plots for d in district_details),
        oldest_plot_time=min(d.oldest_plot_time for d in district_details)
    )


# ==== WS ====
@app.on_event("startup")
async def connect_broadcast():
    await ws.manager.connect()
    asyncio.create_task(ws.broadcast_loop())


@app.on_event("shutdown")
async def disconnect_broadcast():
    await ws.manager.disconnect()


@app.websocket("/ws")
async def plot_updates(websocket: WebSocket):
    await ws.connect(websocket)


# ==== dev test ====
from fastapi.responses import HTMLResponse


@app.get("/")
async def get():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Chat</title>
        </head>
        <body>
            <ul id='messages'>
            </ul>
            <script>
                var ws = new WebSocket(`ws://localhost:8000/ws`);
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };
            </script>
        </body>
    </html>
    """)
