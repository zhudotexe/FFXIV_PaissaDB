from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from . import config, crud, gamedata, models, schemas
from .database import engine, get_db, SessionLocal

models.Base.metadata.create_all(bind=engine)
with SessionLocal() as sess:
    gamedata.upsert_all(gamedata_dir=config.GAMEDATA_DIR, db=sess)

app = FastAPI()


@app.post("/wardInfo", status_code=201)
def ingest_wardinfo(wardinfo: schemas.ffxiv.HousingWardInfo, db: Session = Depends(get_db)):
    print("I got wardinfo")
    print(wardinfo.json(indent=2))
    return {"message": "OK"}


@app.post("/hello")
def hello(data: schemas.paissa.Hello, db: Session = Depends(get_db)):
    crud.upsert_sweeper(db, data)
    return {"message": "OK"}


@app.get("/worlds")
def list_worlds(db: Session = Depends(get_db)):
    return db.query(models.World).all()
