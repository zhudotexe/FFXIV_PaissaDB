import datetime
from typing import Optional

from sqlalchemy.orm import Session

from . import models, schemas


def upsert_sweeper(db: Session, sweeper: schemas.paissa.Hello):
    db_sweeper = models.Sweeper(id=sweeper.cid, name=sweeper.name, world_id=sweeper.worldId)
    merged = db.merge(db_sweeper)
    db.commit()
    return merged


# ---- ingest ----
def _ingest(db: Session, event: schemas.ffxiv.BaseFFXIVPacket, sweeper: Optional[schemas.paissa.JWTSweeper]):
    """Logs the packet to the events table. Does not commit - ingest method that calls this should."""
    sweeper_id = sweeper.cid if sweeper is not None else None
    db_event = models.Event(
        sweeper_id=sweeper_id,
        timestamp=datetime.datetime.now(),
        event_type=event.event_type,
        data=event.json()
    )
    db.add(db_event)
    return db_event


def ingest_wardinfo(db: Session, wardinfo: schemas.ffxiv.HousingWardInfo, sweeper: Optional[schemas.paissa.JWTSweeper]):
    event = _ingest(db, wardinfo, sweeper)
    db_wardsweep = models.WardSweep(
        sweeper_id=event.sweeper_id,
        world_id=wardinfo.LandIdent.WorldId,
        territory_type_id=wardinfo.LandIdent.TerritoryTypeId,
        ward_number=wardinfo.LandIdent.WardNumber,
        timestamp=event.timestamp,
    )

    plots = []
    for i, plot in enumerate(wardinfo.HouseInfoEntries):
        db_plot = models.Plot(
            # plot location info
            world_id=wardinfo.LandIdent.WorldId,
            territory_type_id=wardinfo.LandIdent.TerritoryTypeId,
            ward_number=wardinfo.LandIdent.WardNumber,
            plot_number=i,
            timestamp=event.timestamp,
            # plot info
            is_owned=bool(plot.InfoFlags & schemas.ffxiv.HousingFlags.PlotOwned),
            has_built_house=bool(plot.InfoFlags & schemas.ffxiv.HousingFlags.HouseBuilt),
            house_price=plot.HousePrice,
            owner_name=plot.EstateOwnerName,
            # references
            sweep=db_wardsweep,
            event=event,
        )
        plots.append(db_plot)
    # commit
    db_wardsweep.plots = plots
    event.plots = plots
    db.add(db_wardsweep)
    db.add_all(plots)
    db.commit()
    db.refresh(db_wardsweep)
    return db_wardsweep
