# Changelog

## Project: Aether Wireless RAG Platform

**Current Version:** v0.1.9

## Roadmap Overview

| Version | Feature Domain | Key Objective | Status |
| ------- | -------------- | ------------- | ------ |
| v0.1.9  | Ingestion Tests | Unit test suites for parsers, chunking, lifecycle, embeddings | Done |
| v0.1.8  | Embeddings     | LiteLLM embedding generator with token metering | Done |
| v0.1.7  | Chunking       | Recursive, Semantic, Token, Parent-Child splitters | Done |
| v0.1.6  | Parsers        | Document layout parsers (PDF, DOCX, HTML, CSV) | Done |
| v0.1.5  | API & Dashboard | FastAPI REST API, Health endpoints, Ingestion API, Streamlit Dashboard | Done |
| v0.1.4  | Empty Pipeline | Empty ingestion pipeline orchestrator | Done |
| v0.1.3  | Database       | Alembic migrations, domain entities, repositories, pipeline_runs table | Done |
| v0.1.2  | Config System   | Repository architecture, externalized YAML configs, Pydantic validation engine | Done |
| v0.1.1  | Foundation      | Project scaffold, uv environment, Docker, PostgreSQL/pgvector, configs/ YAML system | Done |
| v0.1.0  | Foundation      | Environment setup, project scaffold, tooling (Ruff, MyPy, Pytest) | Done |

## v0.1.9 (2026-09-13)

### Added

- **Ingestion pipeline tests:** unit test suites for the ingestion modules - `tests/unit/test_lifecycle.py` (version manager & SHA-256 conflict resolution, 16 tests), `tests/unit/test_parsers.py` (parser registry, PlainText/HTML/CSV parsing, PDF/DOCX install hints, 22 tests), `tests/unit/test_chunking.py` (helpers, Recursive/Token/Semantic/ParentChild chunkers, factory routing, 26 tests), and `tests/unit/test_embeddings.py` (token metering, base generator batching/dimension guards, LiteLLM retries + install hint, 21 tests). Full suite passes with ruff and mypy clean

## v0.1.8 (2026-09-13)

### Added

- **Embedding generation:** `app/ingestion/embeddings/` - LiteLLM embedding generator with token metering. `BaseEmbeddingGenerator` contract driven by `EmbeddingConfig` (provider, model, dimensions, batch size) with empty-text guards and per-batch dimension validation. `TokenMeter` tracks input tokens per batch, batch count, and estimated USD cost from `pricing.embedding_usd_per_1m_tokens`. `LiteLLMEmbeddingGenerator` resolved via opt-in `litellm` import with request timeout, exponential-backoff retries, and provider usage token accounting; `get_embedding_generator()` factory

## v0.1.7 (2026-09-13)

### Added

- **Chunking splitters:** `app/ingestion/chunking/` - dependency-free splitters producing `Chunk` entities from raw text: `RecursiveChunker` (paragraph→sentence→word cascade), `TokenChunker` (estimated-token budget with overlap), `SemanticChunker` (embedding-similarity boundaries with injectable `Embedder`, sentence packing fallback), and `ParentChildChunker` (PARENT/CHILD hierarchy linked via `parent_chunk_id` using char offsets). `get_chunker()` factory resolves the active strategy from `configs/pipelines.yaml`
- **Pipeline config:** Added `token` chunking strategy + `TokenChunking` config model (`chunk_size`, `chunk_overlap`)

## v0.1.6 (2026-09-13)

### Added

- **Document parsers:** `app/ingestion/parsers/` - dependency-free `BaseParser` framework with an extension registry: `PlainTextParser` (`.txt`/`.md`/`.markdown`), `HTMLParser` (stdlib `html.parser`; extracts title + headings, drops script/style, readable layout), `CSVParser` (`.csv`/`.tsv` with auto delimiter, UTF-8 BOM handling), `PDFParser` and `DOCXParser` (optional `pypdf`/`python-docx` imports that raise a clear install-hint `ParseError` when missing). `get_parser()` factory with unknown-extension fallback to UTF-8 text; outputs `ParsedDocument` with token/char counts and metadata

## v0.1.5 (2026-09-13)

### Added

- **FastAPI REST API:** `app/api/main.py` initialization with lifespan management, CORS middleware
- **Health endpoints:** `GET /api/v1/health/health`, `/live`, `/ready` for liveness/readiness probes
- **Ingestion API endpoints:** `POST /api/v1/ingestion/run` to trigger pipeline runs, `GET /api/v1/ingestion/runs` for history, `GET /api/v1/ingestion/runs/{run_id}` for run details
- **Streamlit Dashboard:** `ui/app.py` entry point with navigation sidebar, `ui/pages/ingestion.py` dashboard with pipeline trigger button, current run monitoring, and last 5 runs history

### Fixed

- **Pipeline run persistence:** `POST /api/v1/ingestion/run` now `commit()`s the new run (previously only `flush()`ed, so the row was rolled back on session close and `pipeline_runs` stayed empty). Background task also commits completed/failed status updates and marks runs `FAILED` on exception
- **PipelineRun id hydration:** `PipelineRun.__init__` now accepts an `id` argument (defaulting to a new UUID), fixing a `TypeError` in `SQLAlchemyPipelineRunRepository.get()`/`list()` when reconstructing domain models from the ORM

## v0.1.4 (2026-09-13)

### Added

- **Ingestion pipeline:** empty pipeline orchestrator added to `app/ingestion/pipeline.py` with 0 stages for future extension
- **Document discovery:** `FilesystemConnector.scan()` walks the configured input directory (`configs/pipelines.yaml` → `connectors.filesystem.root_path`) recursively, computes SHA-256 checksums, detects MIME types, enforces extension/size/exclusion filters, and yields ready-to-persist `Document` entities
- **Filesystem connector:** `app/ingestion/connectors/filesystem.py` - scans directories recursively for files to index with SHA256 checksums, MIME type detection, configurable extensions/filters
- **Document lifecycle:** `app/ingestion/lifecycle/` - version manager & SHA-256 conflict resolver. `SHA256ConflictResolver` decides `SKIP` (same content as previously indexed, enforced by a unique `documents.checksum_sha256` constraint), `UPDATE` (same path, changed content), `NEW` (no prior record), or `CONFLICT` (ambiguity; configurable content deduplication). `DefaultVersionManager` orchestrates first-time indexing, version bumping with old-version SUPERSEDED, source-metadata refresh, `previous_content_hash` audit trail, and optional old-version ARCHIVED pruning; repository-agnostic via injected path/checksum lookup callables. `ConflictError` aborts before any side effects
- **Pipeline config:** Added filesystem connector config to `configs/pipelines.yaml` with root_path, recursive scan, and exclusion patterns

## v0.1.3 (2026-09-13)

### Added

- **Alembic migration framework:** initialized `alembic/` directory with version control for database schema migrations
- **Pipeline run tracking:** `PipelineRun` domain entity and `pipeline_runs` database table for tracking ingestion execution metrics, FinOps token accounting, and execution audit trails
- **Source metadata:** `app/domain/metadata/source.py` - `SourceMetadata` entity with source type, path, checksum, file info, timestamps
- **Document entity:** `app/domain/models/document.py` - `Document` core entity with versioning (single-active-version), status tracking, and `DocumentVersion` for immutable lineage
- **Document persistence:** SQLAlchemy ORM models (`app/db/models/documents.py`), repositories (`app/db/repositories/document_repository.py`), and interfaces (`app/domain/interfaces/document_repository.py`) for saving documents to PostgreSQL
- **Chunk entity:** `app/domain/models/chunk.py` - `Chunk` core entity with `ChunkType` (parent/child for the parent-child chunking strategy), parent-chunk linkage, content, token/char counts, embedding payload, and metadata
- **Chunk persistence:** `chunks` database table with FK cascade to documents/document_versions, indexed by document and version; `SQLAlchemyChunkRepository` (`app/db/repositories/chunk_repository.py`) and `AbstractChunkRepository` interface (`app/domain/interfaces/chunk_repository.py`) with bulk insert, list-by-document/version, count, and delete operations

## v0.1.2 (2026-09-13)

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

## v0.1.1 (2026-09-13)

### Added

- **Project scaffold:** `pyproject.toml`, package `app/`, `.gitignore`, root documentation (`README.md`, `docs/BRIEF.md`, `CHANGELOG.md`).
- **uv environment & dependency lockfiles:** Python 3.12 virtual environment (`.venv`) and pinned `uv.lock` via `uv sync`.

### Configured

- **pyproject.toml tooling:**
  - **Ruff** (`0.16.7`): line length 120, `py312` target, lint ruleset (E, W, F, I, UP, B, RUF) and formatted output style.
  - **MyPy** (`2.3.1`): strict mode against `app`, `ui`, `tests` with pydantic plugin.
  - **Pytest** (`9.1.1`): `tests/` test discovery with `-ra -q` defaults.

## v0.1.0 (2026-09-13)

### Added

- **Environment setup:** Initial project structure and development environment configuration.