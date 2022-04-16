"""
Schemas defined by FFXIV game code.
See https://github.com/zhudotexe/FFXIV_PaissaHouse/tree/main/Structures
"""
import enum

from pydantic import BaseModel, conlist, constr

from common import models


# ---- substructures ----
class HousingFlags(enum.IntFlag):
    PlotOwned = 1 << 0
    VisitorsAllowed = 1 << 1
    HasSearchComment = 1 << 2
    HouseBuilt = 1 << 3
    OwnedByFC = 1 << 4


class PurchaseType(enum.IntEnum):
    Unavailable = 0
    FCFS = 1
    Lottery = 2


class TenantType(enum.IntEnum):
    FreeCompany = 1
    Personal = 2


class LotteryPhase(enum.IntEnum):
    Available = 1
    Results = 2
    Unavailable = 3


class LandIdent(BaseModel):
    LandId: int
    WardNumber: int
    TerritoryTypeId: int
    WorldId: int


class HouseInfoEntry(BaseModel):
    HousePrice: int
    InfoFlags: HousingFlags
    HouseAppeals: conlist(int, min_items=3, max_items=3)
    EstateOwnerName: constr(max_length=32)


# ---- packets ----
class BaseFFXIVPacket(BaseModel):
    event_type: models.EventType
    client_timestamp: float

    @property
    def timestamp(self):
        return self.client_timestamp

    @classmethod
    def __get_validators__(cls):
        yield cls.return_effect

    @classmethod
    def return_effect(cls, values):  # https://github.com/samuelcolvin/pydantic/issues/619#issuecomment-713508861
        try:
            etype = values["event_type"]
        except KeyError:
            raise ValueError("missing 'event_type' key")
        try:
            return EVENT_TYPES[etype](**values)
        except KeyError:
            raise ValueError(f"{etype} is not a valid event type")


class HousingWardInfo(BaseFFXIVPacket):
    event_type = models.EventType.HOUSING_WARD_INFO
    server_timestamp: float

    LandIdent: LandIdent
    HouseInfoEntries: conlist(HouseInfoEntry, min_items=60, max_items=60)
    PurchaseType: PurchaseType
    TenantType: TenantType

    @property
    def timestamp(self):
        return self.server_timestamp


class LotteryInfo(BaseFFXIVPacket):
    event_type = models.EventType.LOTTERY_INFO

    WorldId: int
    DistrictId: int
    WardId: int
    PlotId: int
    PurchaseType: PurchaseType
    TenantType: TenantType
    AvailabilityType: LotteryPhase
    PhaseEndsAt: int
    EntryCount: int


EVENT_TYPES = {
    models.EventType.HOUSING_WARD_INFO.value: HousingWardInfo,
    models.EventType.LOTTERY_INFO.value: LotteryInfo,
}
