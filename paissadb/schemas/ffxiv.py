"""
Schemas defined by FFXIV game code.
See https://github.com/zhudotexe/FFXIV_PaissaHouse/tree/main/Structures
"""
import enum

from pydantic import BaseModel, conlist, constr


class HousingFlags(enum.IntFlag):
    PlotOwned = 1 << 0
    VisitorsAllowed = 1 << 1
    HasSearchComment = 1 << 2
    HouseBuilt = 1 << 3
    OwnedByFC = 1 << 4


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


class HousingWardInfo(BaseModel):
    LandIdent: LandIdent
    HouseInfoEntries: conlist(HouseInfoEntry, min_items=60, max_items=60)
