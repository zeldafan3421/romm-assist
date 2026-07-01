from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RommModel(BaseModel):
    """Base model that tolerates extra fields RomM's API may return/require.

    RomM's response schemas vary slightly between versions; allowing extra
    fields keeps this project working against minor API drift instead of
    hard-failing validation.
    """

    model_config = ConfigDict(extra="allow")


class Platform(RommModel):
    id: int
    name: str
    slug: str | None = None
    rom_count: int | None = None


class Rom(RommModel):
    id: int
    name: str | None = None
    file_name: str | None = None
    platform_id: int | None = None
    summary: str | None = None
    igdb_id: int | None = None


class RomUpdate(RommModel):
    """Only send the fields you want to change; unset fields are left alone."""

    name: str | None = None
    summary: str | None = None
    igdb_id: int | None = None


class RomSearchResult(RommModel):
    name: str | None = None
    igdb_id: int | None = None
    summary: str | None = None
    cover_url: str | None = None


class Collection(RommModel):
    id: int
    name: str
    description: str | None = None
    rom_ids: list[int] = []


class CollectionCreate(RommModel):
    name: str
    description: str = ""
