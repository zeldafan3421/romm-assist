from __future__ import annotations

from typing import Any

import httpx

from .config import Settings, get_settings
from .models import Collection, Platform, Rom, RomSearchResult


class RommAPIError(RuntimeError):
    """Raised when the RomM API returns an error response."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"RomM API error {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class RommClient:
    """Thin async wrapper around the RomM REST API.

    Authenticates with a Client API Token (preferred) or Basic Auth, both of
    which RomM supports for long-lived companion apps. See RomM's own
    /api/docs on your instance for the authoritative, version-specific
    request/response schemas.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        headers = self._settings.auth_headers()
        auth = None
        if not headers and self._settings.username and self._settings.password:
            auth = (self._settings.username, self._settings.password)
        self._client = httpx.AsyncClient(
            base_url=self._settings.base_url.rstrip("/"),
            headers=headers or None,
            auth=auth,
            timeout=self._settings.timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> RommClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = await self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise RommAPIError(response.status_code, response.text)
        return response

    # -- Platforms ---------------------------------------------------------

    async def list_platforms(self) -> list[Platform]:
        response = await self._request("GET", "/api/platforms")
        return [Platform.model_validate(item) for item in response.json()]

    # -- Roms ----------------------------------------------------------------

    async def list_roms(
        self,
        *,
        platform_id: int | None = None,
        search_term: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Rom]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if platform_id is not None:
            params["platform_id"] = platform_id
        if search_term:
            params["search_term"] = search_term
        response = await self._request("GET", "/api/roms", params=params)
        payload = response.json()
        items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
        return [Rom.model_validate(item) for item in items]

    async def get_rom(self, rom_id: int) -> Rom:
        response = await self._request("GET", f"/api/roms/{rom_id}")
        return Rom.model_validate(response.json())

    async def update_rom(self, rom_id: int, **fields: Any) -> Rom:
        response = await self._request("PUT", f"/api/roms/{rom_id}", json=fields)
        return Rom.model_validate(response.json())

    async def delete_rom(self, rom_id: int, *, delete_from_filesystem: bool = False) -> None:
        await self._request(
            "DELETE",
            f"/api/roms/{rom_id}",
            json={"delete_from_fs": delete_from_filesystem},
        )

    async def search_rom_metadata(
        self, rom_id: int, *, search_term: str | None = None
    ) -> list[RomSearchResult]:
        params: dict[str, Any] = {"rom_id": rom_id}
        if search_term:
            params["search_term"] = search_term
        response = await self._request("GET", "/api/search/roms", params=params)
        return [RomSearchResult.model_validate(item) for item in response.json()]

    # -- Collections -----------------------------------------------------

    async def list_collections(self) -> list[Collection]:
        response = await self._request("GET", "/api/collections")
        return [Collection.model_validate(item) for item in response.json()]

    async def get_collection(self, collection_id: int) -> Collection:
        response = await self._request("GET", f"/api/collections/{collection_id}")
        return Collection.model_validate(response.json())

    async def create_collection(self, name: str, *, description: str = "") -> Collection:
        response = await self._request(
            "POST", "/api/collections", json={"name": name, "description": description}
        )
        return Collection.model_validate(response.json())

    async def set_collection_roms(self, collection_id: int, rom_ids: list[int]) -> Collection:
        response = await self._request(
            "PUT", f"/api/collections/{collection_id}", json={"rom_ids": rom_ids}
        )
        return Collection.model_validate(response.json())

    async def add_rom_to_collection(self, collection_id: int, rom_id: int) -> Collection:
        collection = await self.get_collection(collection_id)
        rom_ids = collection.rom_ids + [rom_id] if rom_id not in collection.rom_ids else collection.rom_ids
        return await self.set_collection_roms(collection_id, rom_ids)

    async def remove_rom_from_collection(self, collection_id: int, rom_id: int) -> Collection:
        collection = await self.get_collection(collection_id)
        rom_ids = [existing for existing in collection.rom_ids if existing != rom_id]
        return await self.set_collection_roms(collection_id, rom_ids)

    # -- Stats -----------------------------------------------------------

    async def stats(self) -> dict[str, Any]:
        response = await self._request("GET", "/api/stats")
        return response.json()
