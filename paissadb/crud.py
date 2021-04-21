import datetime
from typing import Iterator, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session, aliased

from . import config, models, schemas


def upsert_sweeper(db: Session, sweeper: schemas.paissa.Hello) -> models.Sweeper:
    db_sweeper = models.Sweeper(id=sweeper.cid, name=sweeper.name, world_id=sweeper.worldId)
    merged = db.merge(db_sweeper)
    db.commit()
    return merged


def get_worlds(db: Session) -> List[models.World]:
    return db.query(models.World).all()


def get_world_by_id(db: Session, world_id: int) -> models.World:
    return db.query(models.World).filter(models.World.id == world_id).first()


def get_districts(db: Session) -> List[models.District]:
    return db.query(models.District).all()


def get_latest_plots_in_district(db: Session, world_id: int, district_id: int) -> List[models.Plot]:
    """
    sqlite:
    SELECT * FROM plots
    JOIN (
        SELECT plots.id AS id, max(plots.timestamp) AS max_1
        FROM plots
        WHERE plots.world_id = ?
            AND plots.territory_type_id = ?
        GROUP BY plots.ward_number, plots.plot_number
    ) AS latest_plots
        ON plots.id = latest_plots.id

    postgres:
    SELECT DISTINCT ON (ward_number, plot_number) *
        FROM plots
        WHERE world_id = ?
            AND territory_type_id = ?
        ORDER BY ward_number, plot_number, timestamp DESC
    """
    if config.DB_TYPE == 'postgres':
        stmt = db.query(models.Plot) \
            .distinct(models.Plot.ward_number, models.Plot.plot_number) \
            .filter(models.Plot.world_id == world_id, models.Plot.territory_type_id == district_id) \
            .order_by(models.Plot.ward_number, models.Plot.plot_number, desc(models.Plot.timestamp))
    else:
        subq = db.query(models.Plot.id, func.max(models.Plot.timestamp)) \
            .filter(models.Plot.world_id == world_id, models.Plot.territory_type_id == district_id) \
            .group_by(models.Plot.ward_number, models.Plot.plot_number) \
            .subquery()
        latest_plots = aliased(models.Plot, subq)
        stmt = db.query(models.Plot).join(latest_plots, models.Plot.id == latest_plots.id)
    return stmt.all()


def plot_history(db: Session, plot: models.Plot) -> Iterator[models.Plot]:
    return db.query(models.Plot) \
        .filter(models.Plot.world_id == plot.world_id,
                models.Plot.territory_type_id == plot.territory_type_id,
                models.Plot.ward_number == plot.ward_number,
                models.Plot.plot_number == plot.plot_number) \
        .order_by(desc(models.Plot.timestamp)) \
        .yield_per(100)


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


def ingest_wardinfo(
        db: Session,
        wardinfo: schemas.ffxiv.HousingWardInfo,
        sweeper: Optional[schemas.paissa.JWTSweeper]) -> models.WardSweep:
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
