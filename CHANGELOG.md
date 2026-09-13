# Changelog

## Project: Aether Wireless RAG Platform

**Current Version:** v0.1.2-dev

## Roadmap Overview

| Version | Feature Domain | Key Objective | Status |
| ------- | -------------- | ------------- | ------ |
| v0.1.0  | Foundation      | Environment, project scaffold, Docker, PostgreSQL/pgvector, configs/ YAML system | Done |
| v0.1.1  | Config System   | Repository architecture, externalized YAML configs, Pydantic validation engine | Done |
| v0.1.2  | Test Suite      | Unit tests for config system, conftest fixtures, pytest coverage | Done |
| v0.1.3  | Infrastructure  | Docker Compose with PostgreSQL (pgvector), MinIO, OpenTelemetry, Jaeger, Prometheus | In Progress |

## v0.1.1-dev (Unreleased)

### Added

- **Repository architecture:** full `app/` package tree (api, core, db, domain, storage, tasks, ingestion, retrieval, evaluation) and `configs/` with clean separation via package `__init__.py` markers.
- **Externalized operational configs** in `configs/`:
  - `configs/llm.yaml` — chat primary/fallback models, temperature, max tokens, embedding provider/dimensions, resilience timeouts, and USD FinOps pricing rates.
  - `configs/prompts.yaml` — versioned system prompts, citation instructions, and required dynamic variables per prompt.
  - `configs/pipelines.yaml` — ingestion file caps, chunking strategies (recursive / semantic / parent-child), RRF constants, and cross-encoder re-ranking thresholds.
  - `configs/database.yaml` — connection pooling, pgvector HNSW index (`m`, `ef_construction`), and tsvector full-text dictionaries.
- **Config engine** in `app/core/config.py`:
  - `Settings` (pydantic-settings, `AETHER_*` env prefix) resolving `configs/` path and environment.
  - Strict Pydantic models (`LLMConfig`, `PromptsConfig`, `PipelinesConfig`, `DatabaseConfig`) with `extra="forbid"` and cross-field validators (HNSW `m`/`ef_construction`, embedding dims vs vector index dims).
  - `load_runtime_config()` aggregating into a validated `RuntimeConfig`, wrapping failures as `ConfigLoadError` / `ConfigValidationError`.
  - `types-pyYAML` stubs added to the dev dependency group for MyPy typing.

## v0.1.0-dev (2026-09-13)

### Added

- **Project scaffold:** `pyproject.toml`, package `app/`, `.gitignore`, root documentation (`README.md`, `docs/BRIEF.md`, `CHANGELOG.md`).
- **uv environment & dependency lockfiles:** Python 3.12 virtual environment (`.venv`) and pinned `uv.lock` via `uv sync`.

### Configured

- **pyproject.toml tooling:**
  - **Ruff** (`0.16.7`): line length 120, `py312` target, lint ruleset (E, W, F, I, UP, B, RUF) and formatted output style.
  - **MyPy** (`2.3.1`): strict mode against `app`, `ui`, `tests` with pydantic plugin.
  - **Pytest** (`9.1.1`): `tests/` test discovery with `-ra -q` defaults.
## v0.1.3-dev (Unreleased)

### Added
- **Infrastructure:** Docker Compose with PostgreSQL (pgvector), MinIO object storage, OpenTelemetry collector, Jaeger tracing, and Prometheus metrics.
