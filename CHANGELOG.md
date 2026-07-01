# Changelog

All notable changes to this project are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-07-01

### Added

- FastAPI **OpenAPI tool server** wrapping the RomM REST API: platforms,
  ROMs (list/search/get/update/delete), collections, metadata-match search,
  and library stats — all self-documenting via `/openapi.json` for agent
  tool loaders such as Open WebUI.
- Async `RommClient`, authenticated via RomM Client API Tokens (preferred)
  or Basic Auth, with permissive Pydantic models tolerant of minor RomM API
  drift across versions.
- Containerized: a `Dockerfile`/`Containerfile` that builds and runs
  identically under Docker or Podman.
- `docker-compose.yml` for Docker/Podman Compose, and plain Kubernetes
  manifests in `k8s/` for `kubectl` or rootless `podman kube play` — no
  Helm or Kustomize required.
- Optional, genuinely separate local LLM backend (llama.cpp serving
  Qwen2.5-1.5B-Instruct) for fully local agentic use with no external LLM
  API key, wired up for use as an Open WebUI model backend alongside the
  tool server.
- CI: test suite, Docker Compose and Kubernetes manifest validation, Docker
  and Podman image builds, a live `podman kube play` smoke test, and
  automatic image publishing to GHCR on pushes and version tags.

[Unreleased]: https://github.com/zeldafan3421/romm-assist/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/zeldafan3421/romm-assist/releases/tag/v0.1.0
