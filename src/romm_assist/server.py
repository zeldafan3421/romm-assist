from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import NoReturn

from fastapi import Depends, FastAPI, HTTPException, Query

from .client import RommAPIError, RommClient
from .models import Collection, CollectionCreate, Platform, Rom, RomSearchResult, RomUpdate


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.romm_client = RommClient()
    try:
        yield
    finally:
        await app.state.romm_client.aclose()


app = FastAPI(
    title="RomM Assist",
    description=(
        "OpenAPI tool server exposing RomM game-library operations "
        "(platforms, ROMs, collections, metadata search) for agentic use."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


def get_client() -> RommClient:
    return app.state.romm_client


def _raise_for_romm_error(exc: RommAPIError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.get("/health", summary="Liveness check for the tool server process itself", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/platforms",
    response_model=list[Platform],
    summary="List all platforms in the RomM library",
)
async def list_platforms(client: RommClient = Depends(get_client)) -> list[Platform]:
    try:
        return await client.list_platforms()
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.get(
    "/roms",
    response_model=list[Rom],
    summary="List or search ROMs, optionally filtered by platform or a search term",
)
async def list_roms(
    platform_id: int | None = Query(default=None),
    search_term: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    client: RommClient = Depends(get_client),
) -> list[Rom]:
    try:
        return await client.list_roms(
            platform_id=platform_id, search_term=search_term, limit=limit, offset=offset
        )
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.get("/roms/{rom_id}", response_model=Rom, summary="Get full details for a single ROM")
async def get_rom(rom_id: int, client: RommClient = Depends(get_client)) -> Rom:
    try:
        return await client.get_rom(rom_id)
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.patch(
    "/roms/{rom_id}",
    response_model=Rom,
    summary="Update editable metadata fields on a ROM (only send the fields you want to change)",
)
async def update_rom(
    rom_id: int, payload: RomUpdate, client: RommClient = Depends(get_client)
) -> Rom:
    try:
        fields = payload.model_dump(exclude_unset=True)
        return await client.update_rom(rom_id, **fields)
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.delete("/roms/{rom_id}", status_code=204, summary="Delete a ROM from the library")
async def delete_rom(
    rom_id: int,
    delete_from_filesystem: bool = Query(
        default=False,
        description="Also delete the ROM file from disk, not just the library entry",
    ),
    client: RommClient = Depends(get_client),
) -> None:
    try:
        await client.delete_rom(rom_id, delete_from_filesystem=delete_from_filesystem)
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.get(
    "/roms/{rom_id}/metadata-matches",
    response_model=list[RomSearchResult],
    summary="Search metadata providers for candidate matches for a ROM, "
    "useful for fixing unidentified or mismatched games",
)
async def search_rom_metadata(
    rom_id: int,
    search_term: str | None = Query(default=None),
    client: RommClient = Depends(get_client),
) -> list[RomSearchResult]:
    try:
        return await client.search_rom_metadata(rom_id, search_term=search_term)
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.get("/collections", response_model=list[Collection], summary="List all collections")
async def list_collections(client: RommClient = Depends(get_client)) -> list[Collection]:
    try:
        return await client.list_collections()
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.post("/collections", response_model=Collection, summary="Create a new collection")
async def create_collection(
    payload: CollectionCreate, client: RommClient = Depends(get_client)
) -> Collection:
    try:
        return await client.create_collection(payload.name, description=payload.description)
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.post(
    "/collections/{collection_id}/roms/{rom_id}",
    response_model=Collection,
    summary="Add a ROM to a collection",
)
async def add_rom_to_collection(
    collection_id: int, rom_id: int, client: RommClient = Depends(get_client)
) -> Collection:
    try:
        return await client.add_rom_to_collection(collection_id, rom_id)
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.delete(
    "/collections/{collection_id}/roms/{rom_id}",
    response_model=Collection,
    summary="Remove a ROM from a collection",
)
async def remove_rom_from_collection(
    collection_id: int, rom_id: int, client: RommClient = Depends(get_client)
) -> Collection:
    try:
        return await client.remove_rom_from_collection(collection_id, rom_id)
    except RommAPIError as exc:
        _raise_for_romm_error(exc)


@app.get("/stats", summary="Get overall RomM library statistics")
async def get_library_stats(client: RommClient = Depends(get_client)) -> dict:
    try:
        return await client.stats()
    except RommAPIError as exc:
        _raise_for_romm_error(exc)
