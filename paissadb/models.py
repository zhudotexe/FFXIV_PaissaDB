from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import relationship

from .database import Base


class Sweeper(Base):
    __tablename__ = "sweepers"

    id = Column(Integer, primary_key=True, index=True)
    cid = Column(BigInteger, unique=True, index=True)
    name = Column(String)
    world_id = Column(Integer, ForeignKey("worlds.id"))

    world = relationship("World", back_populates="sweepers")
    sweeps = relationship("WardSweep", back_populates="sweeper")


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
    name = Column(String)
    land_set_id = Column(Integer)


class WardSweep(Base):
    __tablename__ = "wardsweeps"

    id = Column(Integer, primary_key=True, index=True)
    cid = Column(Integer, ForeignKey("sweepers.cid"))
    world_id = Column(Integer, ForeignKey("worlds.id"))
    territory_type_id = Column(Integer, ForeignKey("districts.id"))
    ward_number = Column(Integer, index=True)
    timestamp = Column(DateTime, index=True)

    sweeper = relationship("Sweeper", back_populates="sweeps")
    world = relationship("World", back_populates="sweeps")
    plots = relationship("Plot", back_populates="sweep")
    district = relationship("District")


class Plot(Base):
    __tablename__ = "plots"

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id"))
    territory_type_id = Column(Integer, ForeignKey("plotinfo.territory_type_id"))
    ward_number = Column(Integer, index=True)
    plot_number = Column(Integer, ForeignKey("plotinfo.plot_number"))
    sweep_id = Column(Integer, ForeignKey("wardsweeps.id"))

    # HouseInfoEntry
    house_price = Column(Integer)
    info_flags = Column(Integer, index=True)
    house_appeal_1 = Column(SmallInteger, nullable=True)
    house_appeal_2 = Column(SmallInteger, nullable=True)
    house_appeal_3 = Column(SmallInteger, nullable=True)
    owner_name = Column(String, nullable=True)

    sweep = relationship("WardSweep", back_populates="plots")
    world = relationship("World", back_populates="plots")
    plot_info = relationship("PlotInfo", foreign_keys=[territory_type_id, plot_number])


class PlotInfo(Base):
    __tablename__ = "plotinfo"

    id = Column(Integer, primary_key=True, index=True)
    territory_type_id = Column(Integer, ForeignKey("districts.id"))
    plot_number = Column(Integer, index=True)

    house_size = Column(Integer)
    house_base_price = Column(Integer)

    district = relationship("District")
