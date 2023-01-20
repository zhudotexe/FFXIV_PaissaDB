import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UnicodeText,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base

UNKNOWN_OWNER = "Unknown"


class EventType(enum.Enum):
    HOUSING_WARD_INFO = "HOUSING_WARD_INFO"
    LOTTERY_INFO = "LOTTERY_INFO"


# ==== Table defs ====
class Sweeper(Base):
    __tablename__ = "sweepers"

    id = Column(BigInteger, primary_key=True)
    name = Column(String)
    world_id = Column(Integer, ForeignKey("worlds.id"))
    last_seen = Column(DateTime, nullable=True, server_default=func.now(), onupdate=func.now())

    world = relationship("World", back_populates="sweepers")
    events = relationship("Event", back_populates="sweeper")


class World(Base):
    __tablename__ = "worlds"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    datacenter_id = Column(Integer)
    datacenter_name = Column(String)

    sweepers = relationship("Sweeper", back_populates="world")


class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True)  # territoryTypeId
    name = Column(String, unique=True)
    land_set_id = Column(Integer, unique=True, index=True)


class PlotInfo(Base):
    __tablename__ = "plotinfo"

    territory_type_id = Column(Integer, ForeignKey("districts.id"), primary_key=True)
    plot_number = Column(Integer, primary_key=True)

    house_size = Column(Integer)
    house_base_price = Column(Integer)

    district = relationship("District", viewonly=True)


class PlotState(Base):
    __tablename__ = "plot_states"
    __table_args__ = (
        ForeignKeyConstraint(
            ("territory_type_id", "plot_number"), ("plotinfo.territory_type_id", "plotinfo.plot_number")
        ),
    )

    id = Column(Integer, primary_key=True)
    world_id = Column(Integer, ForeignKey("worlds.id"))
    territory_type_id = Column(Integer, ForeignKey("districts.id"))
    ward_number = Column(Integer)
    plot_number = Column(Integer)
    last_seen = Column(Float)  # UNIX seconds
    first_seen = Column(Float)

    is_owned = Column(Boolean)
    last_seen_price = Column(Integer, nullable=True)  # null for unknown price
    owner_name = Column(String, nullable=True)  # "Unknown" for unknown owner (UNKNOWN_OWNER), used to build relo graph

    purchase_system = Column(Integer)
    lotto_entries = Column(Integer, nullable=True)  # null if the plot is FCFS (purchase_system is even)
    lotto_phase = Column(Integer, nullable=True)
    lotto_phase_until = Column(Integer, nullable=True)

    world = relationship("World", viewonly=True)
    district = relationship("District", viewonly=True)
    plot_info = relationship("PlotInfo", viewonly=True)


# common query indices
Index(
    "ix_plot_states_loc_last_seen_desc",
    # these 4 make up the plot state's unique location
    PlotState.world_id,
    PlotState.territory_type_id,
    PlotState.ward_number,
    PlotState.plot_number,
    # and this is for convenience
    PlotState.last_seen.desc(),
)
Index("ix_plot_states_last_seen_desc", PlotState.last_seen.desc())


class LatestPlotState(Base):
    __tablename__ = "latest_plot_states"
    __table_args__ = (
        ForeignKeyConstraint(
            ("territory_type_id", "plot_number"), ("plotinfo.territory_type_id", "plotinfo.plot_number")
        ),
        UniqueConstraint("world_id", "territory_type_id", "ward_number", "plot_number", name="uc_latest_plot_states"),
    )

    id = Column(Integer, primary_key=True)
    world_id = Column(Integer, ForeignKey("worlds.id"))
    territory_type_id = Column(Integer, ForeignKey("districts.id"))
    ward_number = Column(Integer)
    plot_number = Column(Integer)
    state_id = Column(Integer, ForeignKey("plot_states.id"))

    world = relationship("World", viewonly=True)
    district = relationship("District", viewonly=True)
    plot_info = relationship("PlotInfo", viewonly=True)
    state = relationship("PlotState", viewonly=True)


# store of all ingested events for later analysis (e.g. FC/player ownership, relocation/resell graphs, etc)
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    sweeper_id = Column(BigInteger, ForeignKey("sweepers.id", ondelete="SET NULL"), nullable=True, index=True)
    timestamp = Column(Float, index=True)
    event_type = Column(Enum(EventType), index=True)
    data = Column(UnicodeText)

    sweeper = relationship("Sweeper", back_populates="events")
