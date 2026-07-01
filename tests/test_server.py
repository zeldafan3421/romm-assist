from __future__ import annotations

from fastapi.testclient import TestClient

from romm_assist.models import Platform
from romm_assist.server import app, get_client


class FakeRommClient:
    async def list_platforms(self) -> list[Platform]:
        return [Platform(id=1, name="GBA", slug="gba")]


def test_list_platforms_endpoint():
    app.dependency_overrides[get_client] = lambda: FakeRommClient()
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/platforms")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "GBA"


def test_openapi_schema_is_served():
    with TestClient(app) as test_client:
        response = test_client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "RomM Assist"
    assert "/roms/{rom_id}" in schema["paths"]
