from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/wardInfo")
def ingest_wardinfo(wardinfo: schemas.ffxiv.HousingWardInfo, db: Session = Depends(get_db)):
    print("I got wardinfo")
    print(wardinfo.json(indent=2))
    return {"message": "OK"}


@app.get("/worlds")
def list_worlds(db: Session = Depends(get_db)):
    return db.query(models.World).all()
