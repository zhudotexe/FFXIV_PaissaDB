from typing import Iterator, List

from sqlalchemy import desc, func, update
from sqlalchemy.orm import Session, aliased

from common import config, models, schemas


# ==== sweepers ====
def upsert_sweeper(db: Session, sweeper: schemas.paissa.Hello) -> models.Sweeper:
    db_sweeper = models.Sweeper(id=sweeper.cid, name=sweeper.name, world_id=sweeper.worldId)
    merged = db.merge(db_sweeper)
    db.commit()
    return merged


def touch_sweeper_by_id(db: Session, sweeper_id: int):
    stmt = update(models.Sweeper).where(models.Sweeper.id == sweeper_id)
    db.execute(stmt)
    db.commit()


# ==== gamedata ====
def get_worlds(db: Session) -> List[models.World]:
    return db.query(models.World).all()


def get_world_by_id(db: Session, world_id: int) -> models.World:
    return db.query(models.World).filter(models.World.id == world_id).first()


def get_districts(db: Session) -> List[models.District]:
    return db.query(models.District).all()


def get_district_by_id(db: Session, district_id: int) -> models.District:
    return db.query(models.District).filter(models.District.id == district_id).first()


# ==== states ====
def historical_plot_state(
    db: Session,
    plot: models.PlotState,
    before: int = None,
    yield_per: int = 10
) -> Iterator[models.PlotState]:
    q = db.query(models.PlotState).filter(
        models.PlotState.world_id == plot.world_id,
        models.PlotState.territory_type_id == plot.territory_type_id,
        models.PlotState.ward_number == plot.ward_number,
        models.PlotState.plot_number == plot.plot_number
    )
    if before is not None:
        q = q.filter(models.PlotState.id < before)
    return q.order_by(desc(models.PlotState.last_seen)).yield_per(yield_per)


def latest_plot_states_in_district(db: Session, world_id: int, district_id: int) -> List[models.PlotState]:
    """
    Gets the latest plot states in the district.
    """
    # sqlite:
    # SELECT * FROM plot_states
    # JOIN (
    #     SELECT plot_states.id AS id, max(plot_states.last_seen) AS max_1
    #     FROM plot_states
    #     WHERE plot_states.world_id = ?
    #         AND plot_states.territory_type_id = ?
    #     GROUP BY plot_states.ward_number, plot_states.plot_number
    # ) AS latest_plots
    #     ON plot_states.id = latest_plots.id;
    #
    # postgres:
    # note that running this query in a postgres connection "upgrades" the transaction to 32MB work mem
    # SET LOCAL work_mem = '32MB';
    # SELECT DISTINCT ON (ward_number, plot_number) *
    #     FROM plot_states
    #     WHERE world_id = ?
    #         AND territory_type_id = ?
    #     ORDER BY ward_number, plot_number, last_seen DESC;

    if config.DB_TYPE == 'postgresql':
        db.execute("SET LOCAL work_mem = '32MB'")
        stmt = db.query(models.PlotState) \
            .distinct(models.PlotState.ward_number, models.PlotState.plot_number) \
            .filter(models.PlotState.world_id == world_id, models.PlotState.territory_type_id == district_id) \
            .order_by(models.PlotState.ward_number, models.PlotState.plot_number, desc(models.PlotState.last_seen))
    else:
        subq = db.query(models.PlotState.id, func.max(models.PlotState.timestamp)) \
            .filter(models.PlotState.world_id == world_id, models.PlotState.territory_type_id == district_id) \
            .group_by(models.PlotState.ward_number, models.PlotState.plot_number) \
            .subquery()
        latest_plots = aliased(models.PlotState, subq)
        stmt = db.query(models.PlotState).join(latest_plots, models.PlotState.id == latest_plots.id)
    result = stmt.all()
    return result


# ==== ingest ====
pass

# def get_plots_by_ids(db: Session, plot_ids: List[int]) -> List[models.Plot]:
#     return db.query(models.Plot).filter(models.Plot.id.in_(plot_ids)).all()
#
#
# def get_latest_plots_in_district(
#     db: Session,
#     world_id: int,
#     district_id: int,
#     use_cache: bool = False
# ) -> List[models.Plot]:
#     """
#     Gets the latest plots in the district. Note that if *use_cache* is True, the returned objects will be
#     detached.
#
#     Warning: slow! (~70ms)
#     """
#     # sqlite:
#     # SELECT * FROM plots
#     # JOIN (
#     #     SELECT plots.id AS id, max(plots.timestamp) AS max_1
#     #     FROM plots
#     #     WHERE plots.world_id = ?
#     #         AND plots.territory_type_id = ?
#     #     GROUP BY plots.ward_number, plots.plot_number
#     # ) AS latest_plots
#     #     ON plots.id = latest_plots.id;
#     #
#     # postgres:
#     # note that running this query in a postgres connection "upgrades" the transaction to 32MB work mem
#     # SET LOCAL work_mem = '32MB';
#     # SELECT DISTINCT ON (ward_number, plot_number) *
#     #     FROM plots
#     #     WHERE world_id = ?
#     #         AND territory_type_id = ?
#     #     ORDER BY ward_number, plot_number, timestamp DESC;
#
#     if use_cache and (cached := district_plot_cache.get((world_id, district_id))) is not None:
#         return get_plots_by_ids(db, cached)
#
#     if config.DB_TYPE == 'postgresql':
#         db.execute("SET LOCAL work_mem = '32MB'")
#         stmt = db.query(models.Plot) \
#             .distinct(models.Plot.ward_number, models.Plot.plot_number) \
#             .filter(models.Plot.world_id == world_id, models.Plot.territory_type_id == district_id) \
#             .order_by(models.Plot.ward_number, models.Plot.plot_number, desc(models.Plot.timestamp))
#     else:
#         subq = db.query(models.Plot.id, func.max(models.Plot.timestamp)) \
#             .filter(models.Plot.world_id == world_id, models.Plot.territory_type_id == district_id) \
#             .group_by(models.Plot.ward_number, models.Plot.plot_number) \
#             .subquery()
#         latest_plots = aliased(models.Plot, subq)
#         stmt = db.query(models.Plot).join(latest_plots, models.Plot.id == latest_plots.id)
#     result = stmt.all()
#     district_plot_cache[world_id, district_id] = [p.id for p in result]
#     return result
#
#
# def get_plot_states_before(
#     db: Session,
#     world_id: int,
#     district_id: int,
#     ward_number: int,
#     before: datetime.datetime
# ) -> List[models.Plot]:
#     """
#     Gets the state of plots in the ward before a given time.
#     """
#     # sqlite:
#     # SELECT * FROM plots
#     # JOIN (
#     #     SELECT plots.id AS id, max(plots.timestamp) AS max_1
#     #     FROM plots
#     #     WHERE plots.world_id = ?
#     #         AND plots.territory_type_id = ?
#     #         AND plots.ward_number = ?
#     #         AND plots.timestamp < ?
#     #     GROUP BY plots.ward_number, plots.plot_number
#     # ) AS latest_plots
#     #     ON plots.id = latest_plots.id;
#     #
#     # postgres:
#     # SELECT DISTINCT ON (plot_number) *
#     #     FROM plots
#     #     WHERE world_id = ?
#     #         AND territory_type_id = ?
#     #         AND ward_number = ?
#     #         AND timestamp < ?
#     #     ORDER BY plot_number, timestamp DESC;
#     plot = models.Plot
#     if config.DB_TYPE == 'postgresql':
#         db.execute("SET LOCAL work_mem = '32MB'")
#         stmt = db.query(plot) \
#             .distinct(plot.plot_number) \
#             .filter(
#             plot.world_id == world_id,
#             plot.territory_type_id == district_id,
#             plot.ward_number == ward_number,
#             plot.timestamp < before
#             ) \
#             .order_by(plot.plot_number, desc(plot.timestamp))
#     else:
#         subq = db.query(plot.id, func.max(plot.timestamp)) \
#             .filter(
#             plot.world_id == world_id,
#             plot.territory_type_id == district_id,
#             plot.ward_number == ward_number,
#             plot.timestamp < before
#             ) \
#             .group_by(plot.plot_number) \
#             .subquery()
#         latest_plots = aliased(plot, subq)
#         stmt = db.query(plot).join(latest_plots, plot.id == latest_plots.id)
#     result = stmt.all()
#     return result
#
#
# def plot_history(db: Session, plot: models.Plot, before: datetime.datetime = None) -> Iterator[models.Plot]:
#     q = db.query(models.Plot) \
#         .filter(
#         models.Plot.world_id == plot.world_id,
#         models.Plot.territory_type_id == plot.territory_type_id,
#         models.Plot.ward_number == plot.ward_number,
#         models.Plot.plot_number == plot.plot_number
#         )
#     if before is not None:
#         q = q.filter(models.Plot.timestamp < before)
#     return q.order_by(desc(models.Plot.timestamp)) \
#         .yield_per(100)
#
#
# # ---- ingest ----
# def _ingest(
#     db: Session,
#     event: schemas.ffxiv.BaseFFXIVPacket,
#     sweeper: Optional[schemas.paissa.JWTSweeper],
#     timestamp: Optional[datetime.datetime]
# ) -> models.Event:
#     """Logs the packet to the events table. Does not commit - ingest method that calls this should."""
#     sweeper_id = sweeper.cid if sweeper is not None else None
#     db_event = models.Event(
#         sweeper_id=sweeper_id,
#         timestamp=timestamp or datetime.datetime.now(),
#         event_type=event.event_type,
#         data=event.json().replace('\x00', '')  # remove any null bytes that might sneak in somehow
#     )
#     db.add(db_event)
#     return db_event
#
#
# def ingest_wardinfo(
#     db: Session,
#     wardinfo: schemas.ffxiv.HousingWardInfo,
#     sweeper: Optional[schemas.paissa.JWTSweeper]
# ) -> models.WardSweep:
#     event = _ingest(db, wardinfo, sweeper, timestamp=wardinfo.ServerTimestamp)
#     db_wardsweep = models.WardSweep(
#         sweeper_id=event.sweeper_id,
#         world_id=wardinfo.LandIdent.WorldId,
#         territory_type_id=wardinfo.LandIdent.TerritoryTypeId,
#         ward_number=wardinfo.LandIdent.WardNumber,
#         timestamp=wardinfo.ServerTimestamp,
#         event=event
#     )
#
#     plots = []
#     for i, plot in enumerate(wardinfo.HouseInfoEntries):
#         is_owned = bool(plot.InfoFlags & schemas.ffxiv.HousingFlags.PlotOwned)
#         owner_name = plot.EstateOwnerName if is_owned else ""
#         db_plot = models.Plot(
#             # plot location info
#             world_id=wardinfo.LandIdent.WorldId,
#             territory_type_id=wardinfo.LandIdent.TerritoryTypeId,
#             ward_number=wardinfo.LandIdent.WardNumber,
#             plot_number=i,
#             timestamp=wardinfo.ServerTimestamp,
#             # plot info
#             is_owned=is_owned,
#             has_built_house=bool(plot.InfoFlags & schemas.ffxiv.HousingFlags.HouseBuilt),
#             house_price=plot.HousePrice,
#             owner_name=owner_name,
#             # references
#             sweep=db_wardsweep,
#             event=event,
#         )
#         plots.append(db_plot)
#     # commit
#     db_wardsweep.plots = plots
#     event.plots = plots
#     db.add(db_wardsweep)
#     db.add_all(plots)
#     db.commit()
#     # db.refresh(db_wardsweep)  # id is populated already >:c
#     # evict stale cache entry
#     district_plot_cache.pop((db_wardsweep.world_id, db_wardsweep.territory_type_id), None)
#     return db_wardsweep
