from __future__ import annotations

import enum
from typing import Any, List, Optional

from pydantic import BaseModel

from . import ffxiv


class PurchaseSystem(enum.IntFlag):
    # default: FREE_COMPANY | INDIVIDUAL (6)
    # FCFS = 0  (implicit by lack of lottery tag)
    LOTTERY = 1
    FREE_COMPANY = 2
    INDIVIDUAL = 4


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
    price: Optional[int]
    is_owned: bool
    owner_name: Optional[str]  # this can be None if the plot is not owned or if we do not know the owner name
    purchase_system: PurchaseSystem
    lotto_entries: Optional[int]  # this can be None if the ward is FCFS or we do not know the number of entries
    lotto_phase: Optional[ffxiv.LotteryPhase]  # None if wars is FCFS or we do not know the phase (HousingWardInfo)
    lotto_phase_until: Optional[int]


# ==== outputs ====
# --- summary ---
class WorldSummary(BaseModel):
    id: int
    name: str
    datacenter_id: int
    datacenter_name: str


# --- detail ---
class OpenPlotDetail(BaseModel):
    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int
    price: int
    last_updated_time: float
    est_time_open_min: float
    est_time_open_max: float
    purchase_system: PurchaseSystem
    lotto_entries: Optional[int]
    lotto_phase: Optional[ffxiv.LotteryPhase]
    lotto_phase_until: Optional[int]


class PlotUpdate(BaseModel):
    """Sent to update clients on the lottery state of a plot."""

    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int
    price: int
    last_updated_time: float
    purchase_system: PurchaseSystem
    lotto_entries: int
    lotto_phase: ffxiv.LotteryPhase
    previous_lotto_phase: Optional[ffxiv.LotteryPhase]
    lotto_phase_until: int


class SoldPlotDetail(BaseModel):
    world_id: int
    district_id: int
    ward_number: int
    plot_number: int
    size: int
    last_updated_time: float
    est_time_sold_min: float
    est_time_sold_max: float


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


class WSPlotUpdate(WSMessage):
    type = "plot_update"
    data: PlotUpdate


class WSPlotSold(WSMessage):
    type = "plot_sold"
    data: SoldPlotDetail
