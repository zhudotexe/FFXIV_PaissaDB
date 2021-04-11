import logging

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import auth, config, crud, gamedata, models, schemas
from .database import SessionLocal, engine, get_db

models.Base.metadata.create_all(bind=engine)
with SessionLocal() as sess:
    gamedata.upsert_all(gamedata_dir=config.GAMEDATA_DIR, db=sess)

log = logging.getLogger(__name__)
app = FastAPI()


@app.post("/wardInfo", status_code=201)
def ingest_wardinfo(
        wardinfo: schemas.ffxiv.HousingWardInfo,
        sweeper: schemas.paissa.JWTSweeper = Depends(auth.required),
        db: Session = Depends(get_db)):
    log.debug("Received wardInfo:")
    log.debug(wardinfo.json(indent=2))
    crud.ingest_wardinfo(db, wardinfo, sweeper)
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


@app.get("/worlds")
def list_worlds(db: Session = Depends(get_db)):
    return db.query(models.World).all()


@app.get("/worlds/{world_id}")
def get_world(world_id: int, db: Session = Depends(get_db)):
    return db.query(models.World).all()
