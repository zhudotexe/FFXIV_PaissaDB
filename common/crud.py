import hashlib
import json
import struct
from typing import Iterator, List, Optional, Tuple

import aioredis.client
from sqlalchemy import desc, func, update
from sqlalchemy.orm import Session, aliased

from . import config, models, schemas, utils
from .database import EVENT_QUEUE_KEY, TTL_ONE_HOUR, redis


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
    world_id: int,
    district_id: int,
    ward_number: int,
    plot_number: int,
    before: float = None,
    yield_per: int = 10,
) -> Iterator[models.PlotState]:
    q = db.query(models.PlotState).filter(
        models.PlotState.world_id == world_id,
        models.PlotState.territory_type_id == district_id,
        models.PlotState.ward_number == ward_number,
        models.PlotState.plot_number == plot_number,
    )
    if before is not None:
        q = q.filter(models.PlotState.last_seen <= before)
    return q.order_by(desc(models.PlotState.last_seen)).yield_per(yield_per)


def last_state_transition(
    db: Session, current_state: models.PlotState
) -> Tuple[Optional[models.PlotState], Optional[models.PlotState]]:
    """Get the most recent pair of states (to, from) in which a given plot transitioned to the *is_owned* state."""
    next_state = current_state

    for state in historical_plot_state(
        db,
        current_state.world_id,
        current_state.territory_type_id,
        current_state.ward_number,
        current_state.plot_number,
        before=current_state.first_seen,
        yield_per=1,
    ):
        if state.is_owned != current_state.is_owned:
            break
        next_state = state
    else:
        return next_state, None
    return next_state, state


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

    if config.DB_TYPE == "postgresql":
        db.execute("SET LOCAL work_mem = '32MB'")
        stmt = (
            db.query(models.PlotState)
            .distinct(models.PlotState.ward_number, models.PlotState.plot_number)
            .filter(models.PlotState.world_id == world_id, models.PlotState.territory_type_id == district_id)
            .order_by(models.PlotState.ward_number, models.PlotState.plot_number, desc(models.PlotState.last_seen))
        )
    else:
        subq = (
            db.query(models.PlotState.id, func.max(models.PlotState.last_seen))
            .filter(models.PlotState.world_id == world_id, models.PlotState.territory_type_id == district_id)
            .group_by(models.PlotState.ward_number, models.PlotState.plot_number)
            .subquery()
        )
        latest_plots = aliased(models.PlotState, subq)
        stmt = db.query(models.PlotState).join(latest_plots, models.PlotState.id == latest_plots.id)
    result = stmt.all()
    return result


# ==== ingest ====
DATUM_KEY_STRUCT = struct.Struct("!IIHH32s")  # world: u32, district: u32, ward: u16, plot: u16, ownername: char[32]


async def bulk_ingest(db: Session, data: List[schemas.ffxiv.BaseFFXIVPacket], sweeper: schemas.paissa.JWTSweeper):
    sweeper_id = sweeper.cid if sweeper is not None else None
    pipeline = redis.pipeline()

    pipeline.multi()
    for datum in data:
        # add to redis - switch on event type
        if isinstance(datum, schemas.ffxiv.HousingWardInfo):
            if datum.LandIdent.WorldId == 0:  # sometimes the server is borked and sends us fully null data
                continue
            await _ingest_wardinfo(pipeline, datum)
        elif isinstance(datum, schemas.ffxiv.LotteryInfo):
            await _ingest_lotteryinfo(pipeline, datum)
        else:
            raise ValueError(f"Unknown event type: {datum.event_type}")

        # add to postgres
        db_event = models.Event(
            sweeper_id=sweeper_id,
            timestamp=datum.server_timestamp,
            event_type=datum.event_type,
            data=datum.json().replace("\x00", ""),  # remove any null bytes that might sneak in somehow
        )
        db.add(db_event)
    await pipeline.execute()
    await utils.executor(db.commit)


# --- wardinfo ---
async def _ingest_wardinfo(pipeline: aioredis.client.Pipeline, wardinfo: schemas.ffxiv.HousingWardInfo):
    world_id = wardinfo.LandIdent.WorldId
    district_id = wardinfo.LandIdent.TerritoryTypeId
    ward_num = wardinfo.LandIdent.WardNumber
    server_timestamp = wardinfo.server_timestamp
    for plot_num, plot in enumerate(wardinfo.HouseInfoEntries):
        is_owned = bool(plot.InfoFlags & schemas.ffxiv.HousingFlags.PlotOwned)
        owner_name = plot.EstateOwnerName if is_owned else ""
        key_data = DATUM_KEY_STRUCT.pack(world_id, district_id, ward_num, plot_num, owner_name.encode())
        hashed = hashlib.sha256(key_data).hexdigest()
        plot_data_key = f"event.wardinfo.plot:{hashed}"
        purchase_system = ffxiv_purchase_info_to_paissa(wardinfo.PurchaseType, wardinfo.TenantType)
        # using pydantic here is really slow so we just make the dict ourselves
        state_entry = dict(
            world_id=world_id,
            district_id=district_id,
            ward_num=ward_num,
            plot_num=plot_num,
            timestamp=server_timestamp,
            price=plot.HousePrice,
            is_owned=is_owned,
            owner_name=owner_name or None,
            purchase_system=purchase_system.value,
            lotto_entries=None,
            lotto_phase=None,
            lotto_phase_until=None,
        )

        await pipeline.set(plot_data_key, json.dumps(state_entry), nx=True, ex=TTL_ONE_HOUR)
        await pipeline.zadd(EVENT_QUEUE_KEY, {plot_data_key: server_timestamp}, nx=True)


# --- lotteryinfo ---
async def _ingest_lotteryinfo(pipeline: aioredis.client.Pipeline, lotteryinfo: schemas.ffxiv.LotteryInfo):
    world_id = lotteryinfo.WorldId
    district_id = lotteryinfo.DistrictId
    ward_num = lotteryinfo.WardId
    plot_num = lotteryinfo.PlotId
    key_data = DATUM_KEY_STRUCT.pack(world_id, district_id, ward_num, plot_num, bytes())
    hashed = hashlib.sha256(key_data).hexdigest()
    plot_data_key = f"event.lotteryinfo.plot:{hashed}"
    purchase_system = ffxiv_purchase_info_to_paissa(lotteryinfo.PurchaseType, lotteryinfo.TenantType)
    state_entry = dict(
        world_id=world_id,
        district_id=district_id,
        ward_num=ward_num,
        plot_num=plot_num,
        timestamp=lotteryinfo.client_timestamp,
        price=None,
        is_owned=False,
        owner_name=None,
        purchase_system=purchase_system.value,
        lotto_entries=lotteryinfo.EntryCount,
        lotto_phase=lotteryinfo.AvailabilityType.value,
        lotto_phase_until=lotteryinfo.PhaseEndsAt,
    )

    await pipeline.set(plot_data_key, json.dumps(state_entry), nx=True, ex=TTL_ONE_HOUR)
    await pipeline.zadd(EVENT_QUEUE_KEY, {plot_data_key: lotteryinfo.client_timestamp}, nx=True)


# --- helpers ---
def ffxiv_purchase_info_to_paissa(
    purchase_type: schemas.ffxiv.PurchaseType, tenant_type: schemas.ffxiv.TenantType
) -> schemas.paissa.PurchaseSystem:
    purchase_system = schemas.paissa.PurchaseSystem(0)
    if purchase_type == schemas.ffxiv.PurchaseType.Lottery:
        purchase_system |= schemas.paissa.PurchaseSystem.LOTTERY
    if tenant_type == schemas.ffxiv.TenantType.Personal:
        purchase_system |= schemas.paissa.PurchaseSystem.INDIVIDUAL
    if tenant_type == schemas.ffxiv.TenantType.FreeCompany:
        purchase_system |= schemas.paissa.PurchaseSystem.FREE_COMPANY
    return purchase_system
