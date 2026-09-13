# Changelog

## Project: Aether Wireless RAG Platform

**Current Version:** v0.1.0-dev

## Roadmap Overview

| Version | Feature Domain | Key Objective | Status |
| ------- | -------------- | ------------- | ------ |
| v0.1.0  | Foundation      | Environment, project scaffold, Docker, PostgreSQL/pgvector, configs/ YAML system | In Progress |

## v0.1.0-dev (Unreleased)

### Added

- **Project scaffold:** `pyproject.toml`, package `app/`, `.gitignore`, root documentation (`README.md`, `docs/BRIEF.md`, `CHANGELOG.md`).
- **uv environment & dependency lockfiles:** Python 3.12 virtual environment (`.venv`) and pinned `uv.lock` via `uv sync`.

### Configured

- **pyproject.toml tooling:**
  - **Ruff** (`0.16.7`): line length 120, `py312` target, lint ruleset (E, W, F, I, UP, B, RUF) and formatted output style.
  - **MyPy** (`2.3.1`): strict mode against `app`, `ui`, `tests` with pydantic plugin.
  - **Pytest** (`9.1.1`): `tests/` test discovery with `-ra -q` defaults.