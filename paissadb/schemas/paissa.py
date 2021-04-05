from __future__ import annotations

from typing import List

from pydantic import BaseModel


# ==== Sweeper ====
class SweeperBase(BaseModel):
    cid: int
    name: str
    world_id: int


class SweeperCreate(SweeperBase):
    pass


class Sweeper(SweeperBase):
    id: int
    world: World
    sweeps: List[WardSweep]

    class Config:
        orm_mode = True


# ==== World ====
class WorldBase(BaseModel):
    id: int
    name: str


class WorldCreate(WorldBase):
    pass


class World(WorldBase):
    sweepers: List[Sweeper]
    sweeps: List[WardSweep]
    plots: List[Plot]

    class Config:
        orm_mode = True


# ==== District ====
class DistrictBase(BaseModel):
    id: int
    name: str
    land_set_id: int


class DistrictCreate(DistrictBase):
    pass


class District(DistrictBase):
    class Config:
        orm_mode = True


# ==== PlotInfo ====
class PlotInfoBase(BaseModel):
    territory_type_id: int
    plot_number: int
    house_size: int
    house_base_price: int


class PlotInfoCreate(PlotInfoBase):
    pass


class PlotInfo(PlotInfoBase):
    district: District

    class Config:
        orm_mode = True


# ==== WardSweep ====
class WardSweepBase(BaseModel):
    cid: int
    world_id: int
    territory_type_id: int
    ward_number: int
    timestamp: int


class WardSweepCreate(WardSweepBase):
    pass


class WardSweep(WardSweepBase):
    id: int
    sweeper: Sweeper
    world: World
    plots: List[Plot]
    district: District

    class Config:
        orm_mode = True


# ==== Plot ====
class PlotBase(BaseModel):
    plot_number: int
    sweep_id: int
    house_price: int
    info_flags: int
    house_appeal_1: int
    house_appeal_2: int
    house_appeal_3: int
    owner_name: str


class PlotCreate(PlotBase):
    pass


class Plot(PlotBase):
    id: int
    world_id: int
    territory_type_id: int
    ward_number: int
    sweep: WardSweep
    world: World
    district: District
    plot_info: PlotInfo

    class Config:
        orm_mode = True
