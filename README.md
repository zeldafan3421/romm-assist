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

## Running in containers

Everything below works with `docker` or `podman` interchangeably — the
compose files use no Docker-specific extensions, and the image builds from
a plain `Dockerfile` (also symlinked as `Containerfile`, since that's what
bare `podman build .` looks for by default). Kubernetes manifests in `k8s/`
are the preferred path, especially for **rootless Podman**; a Docker
Compose setup is fully supported alongside it for anyone who'd rather not
touch YAML.

### Prebuilt image

Every push to the default branch and every `vX.Y.Z` tag is built and
published to GHCR by `.github/workflows/docker.yml` (the same workflow also
builds the image with Podman, and runs it through `podman kube play`, on
every run as a portability check):

```bash
docker pull ghcr.io/zeldafan3421/romm-assist:latest
podman pull ghcr.io/zeldafan3421/romm-assist:latest
```

Pull requests and other branches only build the image (to catch breakage)
without pushing it.

### Kubernetes (kubectl, or rootless Podman via `kube play`)

Plain manifests in `k8s/` — no Helm or Kustomize needed. `podman kube play`
supports the `Deployment`, `PersistentVolumeClaim`, `ConfigMap`, and
`Secret` kinds used here, but not `Service`, so the `*-deployment.yaml`
files (playable by both engines) are split from the `*-service.yaml` files
(real clusters only — kube play instead relies on `hostPort` for direct
host access). `kube play`/`kube down` also only take a single YAML source,
so multiple files are concatenated and piped in via stdin (`-f` on
`kubectl apply`/`delete` has no such limit).

```bash
cp k8s/romm-assist-secret.example.yaml k8s/romm-assist-secret.yaml
# edit k8s/romm-assist-secret.yaml: ROMM_BASE_URL and ROMM_API_TOKEN

# Rootless Podman:
podman login ghcr.io   # only if the image is private
(cat k8s/romm-assist-secret.yaml; echo ---; cat k8s/romm-assist-deployment.yaml) | podman kube play -
curl http://localhost:8000/health

# Real cluster:
kubectl apply -f k8s/romm-assist-secret.yaml -f k8s/romm-assist-deployment.yaml -f k8s/romm-assist-service.yaml
```

Tear down with `(cat k8s/romm-assist-secret.yaml; echo ---; cat k8s/romm-assist-deployment.yaml) | podman kube down -`
or the equivalent `kubectl delete -f ...`.

A few things worth knowing:

- `romm-assist-deployment.yaml` runs as non-root (`runAsUser: 1000`,
  matching the image's `appuser`) and sets `hostPort: 8000` so rootless
  `kube play` is reachable without a Service. A cluster with a restricted
  PodSecurity policy may reject `hostPort` — drop it there and use
  `romm-assist-service.yaml` plus your own Ingress/port-forward instead.
- For a private `ghcr.io/zeldafan3421/romm-assist` image, `kube play`
  doesn't support `imagePullSecrets`, so `podman login ghcr.io` first. On a
  real cluster, `kubectl create secret docker-registry` and uncomment
  `imagePullSecrets` in the Deployment.
- `k8s/validate.py` does a structural sanity check of every manifest (run
  in CI); it's not a substitute for `kubectl apply --dry-run`.

### Docker Compose (Docker or Podman)

```bash
cp .env.example .env   # edit it first
docker compose up --build     # or: podman compose up --build
```

Or without compose:

```bash
docker build -t romm-assist .                                   # or: podman build -t romm-assist .
docker run --rm -p 8000:8000 --env-file .env romm-assist        # or: podman run --rm -p 8000:8000 --env-file .env romm-assist
```

The container exposes port `8000` and includes a `HEALTHCHECK` against
`GET /health`.

## Optional local LLM (llama.cpp)

The LLM backend is a genuinely separate, opt-in deployment in every form
here — `docker-compose.yml` and `k8s/romm-assist-deployment.yaml` have no
knowledge of it at all, and it only exists if you also load
`docker-compose.llm.yml` / apply `k8s/llamacpp-deployment.yaml`. There's no
flag to forget — skip that file and the LLM container is never defined,
built, or started.

Either way it runs [llama.cpp's](https://github.com/ggml-org/llama.cpp)
`llama-server` — a small, self-hosted, OpenAI-API-compatible model server to
drive agentic use of the `romm-assist` tools, with no external LLM API
required. On first start it downloads and caches **Qwen2.5-1.5B-Instruct**
quantized to `Q4_K_M` (~1 GB) directly from Hugging Face — a small model
chosen to run comfortably on CPU while still following tool-calling chat
templates (`--jinja` is enabled for this). Subsequent restarts reuse the
cached weights, no re-download. It's CPU-only and lightweight by default
(`N_GPU_LAYERS=0`, `THREADS=4`, `CTX_SIZE=4096`); tune these, or swap in a
different GGUF model entirely.

The server listens on port `8080` with an OpenAI-compatible API at `/v1/*`,
so it works as a drop-in model backend for Open WebUI or any other
OpenAI-API client, and is reachable from other machines on your network the
same way any published container port is.

### Kubernetes

```bash
podman kube play k8s/llamacpp-deployment.yaml
# or: kubectl apply -f k8s/llamacpp-deployment.yaml -f k8s/llamacpp-service.yaml
```

`llamacpp-deployment.yaml` provisions a `PersistentVolumeClaim`
(`llamacpp-models`) for the cached weights and a `ConfigMap`
(`llamacpp-env`) for the `LLAMA_ARG_*` settings described above — edit the
ConfigMap (or `kubectl edit configmap llamacpp-env`) to change the model or
resource limits. Readiness/liveness probes are deliberately lenient
(`failureThreshold: 60` on readiness) to tolerate the first-time ~1 GB
download; tighten them once the model is cached. If you set an API key, add
a `Secret` with an `LLAMA_API_KEY` key and uncomment the `secretRef` in the
Deployment.

### Docker Compose

```bash
# Without the LLM (default):
docker compose up -d                                                # or: podman compose up -d

# With the LLM:
docker compose -f docker-compose.yml -f docker-compose.llm.yml up -d   # or the podman compose equivalent
```

Tune the model/resources via the `LLAMACPP_*` variables in `.env` (see
`.env.example`). Since RomM's own default port is also `8080`, change
`LLAMACPP_PORT` if that collides on your host. Set `LLAMACPP_API_KEY` if
the port is reachable beyond a trusted network.

### Wiring it into Open WebUI

1. **Model backend** — in Open WebUI, go to Settings -> Connections -> add
   an "OpenAI API" connection with base URL `http://<host>:8080/v1` (any
   value works as the API key unless you set an API key above).
2. **RomM tools** — go to Settings -> Tools -> add an OpenAPI tool server
   with URL `http://<host>:8000/openapi.json` (the `romm-assist` service
   from this repo). This is what actually exposes the RomM library
   operations to the model.

With both connected, chatting through Open WebUI against the Qwen2.5 model
lets it call the `romm-assist` endpoints to browse, search, and manage your
RomM library.

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
required to run the test suite. `python k8s/validate.py` structurally
validates the Kubernetes manifests the same way CI does.
