import enum
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, ForeignKey, ForeignKeyConstraint, Integer, String, \
    UnicodeText
from sqlalchemy.orm import relationship

from .database import Base

UNKNOWN_OWNER = "Unknown"
HOUSING_DEVAL_FACTOR = 0.0042


class EventType(enum.Enum):
    HOUSING_WARD_INFO = "HOUSING_WARD_INFO"
    # LAND_UPDATE (house sold, reloed, autodemoed, etc)
    #   https://github.com/SapphireServer/Sapphire/blob/master/src/common/Network/PacketDef/Zone/ServerZoneDef.h#L1888
    #   https://github.com/SapphireServer/Sapphire/blob/master/src/world/Manager/HousingMgr.cpp#L365
    # LAND_SET_INITIALIZE (sent on zonein)
    #   https://github.com/SapphireServer/Sapphire/blob/master/src/common/Network/PacketDef/Zone/ServerZoneDef.h#L1943
    #   https://github.com/SapphireServer/Sapphire/blob/master/src/world/Territory/HousingZone.cpp#L197
    # LAND_SET_MAP (sent on zonein, after init, probably the useful one)
    #   https://github.com/SapphireServer/Sapphire/blob/master/src/common/Network/PacketDef/Zone/ServerZoneDef.h#L1929
    #   https://github.com/SapphireServer/Sapphire/blob/master/src/world/Territory/HousingZone.cpp#L154
    # other packets:
    #   LAND_INFO_SIGN (view placard on owned house) - probably not useful, if we get this we already got a LAND_SET_MAP
    #       and if the ward changed since then, we got a LAND_UPDATE
    #   LAND_PRICE_UPDATE (view placard on unowned house) - similar to above, plus spammy if someone is buying a house


# ==== Table defs ====
class Sweeper(Base):
    __tablename__ = "sweepers"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String)
    world_id = Column(Integer, ForeignKey("worlds.id"))

    world = relationship("World", back_populates="sweepers")
    sweeps = relationship("WardSweep", back_populates="sweeper")
    events = relationship("Event", back_populates="sweeper")


class World(Base):
    __tablename__ = "worlds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    sweepers = relationship("Sweeper", back_populates="world")
    sweeps = relationship("WardSweep", back_populates="world")
    plots = relationship("Plot", back_populates="world")


class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)  # territoryTypeId
    name = Column(String, unique=True)
    land_set_id = Column(Integer, unique=True, index=True)


class PlotInfo(Base):
    __tablename__ = "plotinfo"

    territory_type_id = Column(Integer, ForeignKey("districts.id"), primary_key=True)
    plot_number = Column(Integer, primary_key=True)

    house_size = Column(Integer)
    house_base_price = Column(Integer)

    district = relationship("District", viewonly=True)


class WardSweep(Base):
    __tablename__ = "wardsweeps"

    id = Column(Integer, primary_key=True, index=True)
    sweeper_id = Column(BigInteger, ForeignKey("sweepers.id"), nullable=True)
    world_id = Column(Integer, ForeignKey("worlds.id"))
    territory_type_id = Column(Integer, ForeignKey("districts.id"))
    ward_number = Column(Integer, index=True)
    timestamp = Column(DateTime, index=True)

    sweeper = relationship("Sweeper", back_populates="sweeps")
    world = relationship("World", back_populates="sweeps")
    plots = relationship("Plot", back_populates="sweep")
    district = relationship("District", viewonly=True)


class Plot(Base):
    __tablename__ = "plots"
    __table_args__ = (
        ForeignKeyConstraint(("territory_type_id", "plot_number"),
                             ("plotinfo.territory_type_id", "plotinfo.plot_number")),
    )

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id"), index=True)
    territory_type_id = Column(Integer, ForeignKey("districts.id"), index=True)
    ward_number = Column(Integer, index=True)
    plot_number = Column(Integer, index=True)
    timestamp = Column(DateTime, index=True)
    sweep_id = Column(Integer, ForeignKey("wardsweeps.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"))

    is_owned = Column(Boolean, index=True)
    has_built_house = Column(Boolean)  # used to determine if a plot was reloed into or bought (not super accurate)
    house_price = Column(Integer, nullable=True)  # null for unknown price
    owner_name = Column(String, nullable=True)  # "Unknown" for unknown owner (UNKNOWN_OWNER), used to build relo graph

    sweep = relationship("WardSweep", back_populates="plots")
    event = relationship("Event", back_populates="plots")
    world = relationship("World", back_populates="plots")
    district = relationship("District", viewonly=True)
    plot_info = relationship("PlotInfo", viewonly=True)

    @property
    def num_devals(self) -> Optional[int]:
        """
        Returns the number of price this house has devalued. If the price is unknown, returns None.
        If price>max, returns 0.
        """
        if self.house_price is None:
            return None
        max_price = self.plot_info.house_base_price
        if self.house_price >= max_price:
            return 0
        return round((max_price - self.house_price) / (HOUSING_DEVAL_FACTOR * max_price))


# store of all ingested events for later analysis (e.g. FC/player ownership, relocation/resell graphs, etc)
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    sweeper_id = Column(BigInteger, ForeignKey("sweepers.id"), nullable=True, index=True)
    timestamp = Column(DateTime, index=True)
    event_type = Column(Enum(EventType), index=True)
    data = Column(UnicodeText)

    sweeper = relationship("Sweeper", back_populates="events")
    plots = relationship("Plot", back_populates="event")
