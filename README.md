# romm-assist

A small Python project that wraps the [RomM](https://github.com/rommapp/romm) REST
API and re-exposes it as an **OpenAPI tool server**, so AI agents (Open WebUI
tools, MCP-via-OpenAPI bridges, or any framework that can import an
`openapi.json`) can manage a RomM game library: list platforms, browse/search
ROMs, edit metadata, delete ROMs, manage collections, and look up metadata
matches for unidentified games.

## How it fits together

```
Agent / Open WebUI  --(OpenAPI tool calls)-->  romm-assist FastAPI server  --(RomM REST API)-->  your RomM instance
```

`romm-assist` itself is a plain FastAPI app. FastAPI auto-generates an
OpenAPI schema at `/openapi.json`, which is exactly what the "OpenAPI tool
server" convention expects — point any compatible agent tool loader at that
URL (or at `http://<host>:8000` for servers that auto-discover it) and it
picks up every endpoint below as a callable tool, with descriptions pulled
straight from the code.

## Project layout

```
src/romm_assist/
  config.py   - Settings (env vars), see .env.example
  client.py   - RommClient: async httpx wrapper around the RomM REST API
  models.py   - Pydantic models shared by the client and the tool server
  server.py   - FastAPI app exposing the tool endpoints
tests/        - respx-mocked client tests + FastAPI TestClient tests
```

## Setup

```bash
uv venv && source .venv/bin/activate   # or python -m venv .venv
uv pip install -e ".[dev]"             # or: pip install -e ".[dev]"

cp .env.example .env
# edit .env: set ROMM_BASE_URL and ROMM_API_TOKEN (or ROMM_USERNAME/ROMM_PASSWORD)
```

Generate a Client API Token from your RomM instance under
**Administration -> Client API Tokens** — these are the long-lived tokens
RomM recommends for companion apps/scripts, as opposed to short-lived OAuth2
tokens. Basic auth is supported as a fallback.

## Running the tool server

```bash
romm-assist
# or: uvicorn romm_assist.server:app --reload
```

This starts the server on `http://localhost:8000`. Interactive docs are at
`/docs`, and the machine-readable schema agents consume is at
`/openapi.json`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/platforms` | List platforms |
| GET | `/roms` | List/search ROMs (`platform_id`, `search_term`, `limit`, `offset`) |
| GET | `/roms/{rom_id}` | Get one ROM |
| PATCH | `/roms/{rom_id}` | Update ROM metadata fields |
| DELETE | `/roms/{rom_id}` | Delete a ROM (optionally `delete_from_filesystem`) |
| GET | `/roms/{rom_id}/metadata-matches` | Search metadata providers for candidate matches |
| GET | `/collections` | List collections |
| POST | `/collections` | Create a collection |
| POST | `/collections/{collection_id}/roms/{rom_id}` | Add a ROM to a collection |
| DELETE | `/collections/{collection_id}/roms/{rom_id}` | Remove a ROM from a collection |
| GET | `/stats` | Library statistics |

## A note on the RomM API surface

RomM's REST API has evolved across versions, and its full schema is only
authoritative on your own instance (`/api/docs` and `/api/redoc`, served
from RomM itself). `client.py` targets the well-established resources
(`/api/platforms`, `/api/roms`, `/api/collections`, `/api/search/roms`,
`/api/stats`) and uses permissive Pydantic models (`extra="allow"`) so minor
field differences don't break parsing. If a call fails against your
instance, check its `/api/docs` and adjust the request in `client.py` — it's
a single small file by design.

## Tests

```bash
pytest
```

Client tests mock RomM's HTTP API with `respx`; no live RomM instance is
required to run the test suite.
