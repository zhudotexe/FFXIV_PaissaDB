from __future__ import annotations

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


# ==== internal ====
class PlotStateEntry(BaseModel):
    """Model used to store some plot data in redis for later processing"""
    world_id: int
    district_id: int
    ward_num: int
    plot_num: int
    timestamp: float
    price: int
    is_owned: bool
    owner_name: Optional[str]
    is_fcfs: bool
    lotto_entries: Optional[int]


# ==== outputs ====
# --- summary ---
class WorldSummary(BaseModel):
    id: int
    name: str


# --- detail ---
class OpenPlotDetail(BaseModel):
    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int
    last_seen_price: int
    last_updated_time: float
    est_time_open_min: float
    est_time_open_max: float


class DistrictDetail(BaseModel):
    id: int
    name: str
    num_open_plots: int
    oldest_plot_time: float
    open_plots: List[OpenPlotDetail]


class WorldDetail(WorldSummary):
    districts: List[DistrictDetail]
    num_open_plots: int
    oldest_plot_time: float


class SoldPlotDetail(BaseModel):
    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int
    last_updated_time: float
    est_time_sold_min: float
    est_time_sold_max: float


class TemporarilyDisabled(BaseModel):
    """Temporary response model used to indicate that an endpoint is disabled due to high load."""
    message: Optional[str]
    until: Optional[float]
    indefinite: bool


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
