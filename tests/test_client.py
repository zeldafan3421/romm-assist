from __future__ import annotations

import httpx
import pytest
import respx

from romm_assist.client import RommAPIError, RommClient
from romm_assist.config import Settings

BASE_URL = "http://romm.test"


def make_client(**overrides: object) -> RommClient:
    settings = Settings(base_url=BASE_URL, api_token="rmm_test", **overrides)
    return RommClient(settings)


@respx.mock
async def test_list_platforms():
    respx.get(f"{BASE_URL}/api/platforms").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "GBA", "slug": "gba"}])
    )
    client = make_client()
    try:
        platforms = await client.list_platforms()
    finally:
        await client.aclose()

    assert len(platforms) == 1
    assert platforms[0].name == "GBA"


@respx.mock
async def test_get_rom_not_found_raises():
    respx.get(f"{BASE_URL}/api/roms/99").mock(return_value=httpx.Response(404, text="Not Found"))
    client = make_client()
    try:
        with pytest.raises(RommAPIError) as exc_info:
            await client.get_rom(99)
    finally:
        await client.aclose()

    assert exc_info.value.status_code == 404


@respx.mock
async def test_update_rom_only_sends_provided_fields():
    route = respx.put(f"{BASE_URL}/api/roms/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "name": "New Name"})
    )
    client = make_client()
    try:
        rom = await client.update_rom(1, name="New Name")
    finally:
        await client.aclose()

    assert rom.name == "New Name"
    assert route.calls.last.request.content == b'{"name":"New Name"}'


@respx.mock
async def test_add_rom_to_collection_merges_ids():
    respx.get(f"{BASE_URL}/api/collections/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "name": "Favorites", "rom_ids": [1, 2]})
    )
    put_route = respx.put(f"{BASE_URL}/api/collections/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "name": "Favorites", "rom_ids": [1, 2, 3]})
    )
    client = make_client()
    try:
        collection = await client.add_rom_to_collection(5, 3)
    finally:
        await client.aclose()

    assert collection.rom_ids == [1, 2, 3]
    assert put_route.called


@respx.mock
async def test_remove_rom_from_collection():
    respx.get(f"{BASE_URL}/api/collections/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "name": "Favorites", "rom_ids": [1, 2, 3]})
    )
    put_route = respx.put(f"{BASE_URL}/api/collections/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "name": "Favorites", "rom_ids": [1, 3]})
    )
    client = make_client()
    try:
        collection = await client.remove_rom_from_collection(5, 2)
    finally:
        await client.aclose()

    assert collection.rom_ids == [1, 3]
    assert put_route.called
