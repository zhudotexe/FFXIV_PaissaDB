from __future__ import annotations

import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


# ==== inputs ====
class Hello(BaseModel):
    cid: int
    name: str
    world: str
    worldId: int


class JWTSweeper(BaseModel):
    cid: Optional[int]


# ==== outputs ====
# --- summary ---
class DistrictSummary(BaseModel):
    id: int
    name: str
    num_open_plots: int
    oldest_plot_time: datetime.datetime


class WorldSummary(BaseModel):
    id: int
    name: str
    districts: List[DistrictSummary]
    num_open_plots: int
    oldest_plot_time: datetime.datetime


# --- detail ---
class OpenPlotDetail(BaseModel):
    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int
    known_price: int
    last_updated_time: datetime.datetime
    est_time_open_min: datetime.datetime
    est_time_open_max: datetime.datetime
    est_num_devals: int


class DistrictDetail(DistrictSummary):
    open_plots: List[OpenPlotDetail]


class WorldDetail(WorldSummary):
    districts: List[DistrictDetail]


class SoldPlotDetail(BaseModel):
    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int
    last_updated_time: datetime.datetime
    est_time_sold_min: datetime.datetime
    est_time_sold_max: datetime.datetime


# ==== websocket ====
class WSMessage(BaseModel):
    type: str
    data: Optional[Any]


class WSPlotOpened(WSMessage):
    type = "plot_open"
    data: OpenPlotDetail


class WSPlotSold(WSMessage):
    type = "plot_sold"
    data: SoldPlotDetail
