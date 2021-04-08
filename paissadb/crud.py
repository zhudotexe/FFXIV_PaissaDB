from sqlalchemy.orm import Session

from . import models, schemas


def upsert_sweeper(db: Session, sweeper: schemas.paissa.Hello):
    db_sweeper = models.Sweeper(cid=sweeper.cid, name=sweeper.name, world_id=sweeper.worldId)
    db.merge(db_sweeper)
    db.commit()
    db.refresh(db_sweeper)
    return db_sweeper
