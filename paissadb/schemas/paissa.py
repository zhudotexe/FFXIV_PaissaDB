from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Hello(BaseModel):
    cid: int
    name: str
    world: str
    worldId: int


class JWTSweeper(BaseModel):
    cid: Optional[int]
