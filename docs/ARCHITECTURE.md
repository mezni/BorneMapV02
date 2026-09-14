# Architecture: Aether Wireless RAG Platform

This document describes the **current** implementation of the platform. It is
the "as-built" companion to `docs/BRIEF.md`, which is the forward-looking
blueprint and project roadmap. Where the code has not yet reached the brief,
this document says so explicitly; the roadmap is tracked in `CHANGELOG.md`.

## 1. Overview

Aether Wireless RAG is a retrieval-augmented generation platform for internal
technical documentation, support runbooks, and network operations policies. It
is built around four architectural pillars that shape every subsystem:

- **Clean Architecture / DDD** — pure domain logic with no framework
  dependencies.
- **Externalized YAML configuration** — every operational parameter lives in
  `configs/*.yaml`, loaded and validated at startup.
- **Immutable document versioning** — SHA-256 content hashing drives
  deduplication and a single-active-version lineage model.
- **FinOps accounting** — embedding token metering and cost estimation are
  first-class concerns, recorded on every pipeline run.

The stack is Python 3.12, FastAPI (API), Streamlit (dashboard), SQLAlchemy +
Alembic + PostgreSQL/pgvector (persistence), and LiteLLM (embedding providers).

## 2. Module Map

```
app/
├── core/            # YAML config + pydantic validation (config.py)
├── domain/          # Pure domain: entities, metadata, repository ABCs
│   ├── models/      #   Document, DocumentVersion, Chunk, PipelineRun
│   ├── metadata/    #   SourceMetadata / SourceType
│   └── interfaces/  #   Abstract*Repository interfaces
├── db/              # Persistence infrastructure
│   ├── models/      #   SQLAlchemy ORM mappings
│   ├── repositories/#   SQLAlchemy implementations of domain interfaces
│   └── session.py   #   Engine, SessionLocal, get_db dependency
├── api/             # FastAPI delivery layer
│   ├── main.py      #   App factory, lifespan, middleware
│   ├── schemas/     #   API request/response models
│   └── v1/          #   v1 router: health + ingestion endpoints
├── ingestion/       # Ingestion engine
│   ├── pipeline.py  #   Orchestrator (currently 0-stage stub)
│   ├── connectors/  #   Filesystem source scanner
│   ├── parsers/     #   PlainText, HTML, CSV, PDF, DOCX (+ registry)
│   ├── chunking/    #   Recursive, Token, Semantic, Parent-Child (+ registry)
│   ├── lifecycle/   #   VersionManager + SHA-256 ConflictResolver
│   └── embeddings/  #   LiteLLM-backed generator + TokenMeter
├── retrieval/       # (planned v0.1.11) stub packages only
└── evaluation/      # (planned) stub packages only

ui/                  # Streamlit dashboard (ingestion dashboard live)
tests/               # pytest suite (unit, class-style)
configs/             # llm.yaml, prompts.yaml, pipelines.yaml, database.yaml
alembic/             # Schema migrations
```

## 3. Layering & Dependency Rules

Dependencies are one-way: `api` → `db` → `domain`, and `ingestion` → `domain`
(plus `core` for config). `app/domain` imports no framework, ORM, HTTP, or
Infrastructure code. This keeps business rules testable in isolation.

- `core` is the config foundation; every other layer may read config.
- `db/repositories` implement the ABCs declared in `domain/interfaces`.
- `api` and `ui` are thin delivery shells over services and repositories.

## 4. Configuration System (`app/core/config.py`)

- `configs/*.yaml` is the single source of truth for operational parameters;
  environment variables (prefix `AETHER_`, `.env` file) are handled by
  `Settings` (pydantic-settings) and currently only override environment and
  `configs_dir`.
- Each YAML maps to a strict Pydantic model (`ConfigDict(extra="forbid")`) with
  bounded numeric fields:
  - `llm.yaml` → `LLMConfig` (chat primary/fallback, embeddings, timeouts, pricing)
  - `prompts.yaml` → `PromptsConfig` (versioned prompt definitions + variables)
  - `pipelines.yaml` → `PipelinesConfig` (ingestion caps, chunking strategies,
    dense/sparse/hybrid/RRF + reranker settings)
  - `database.yaml` → `DatabaseConfig` (connection pool, pgvector HNSW, fulltext)
- `load_runtime_config()` aggregates the four files into a validated
  `RuntimeConfig` and cross-validates invariants:
  - `llm.embeddings.dimensions` must equal `database.vector_index.dims`
  - HNSW `m * 2 <= ef_construction`
  - `retrieval.hybrid.rrf_k` must be positive
- Load failures raise a typed hierarchy: `ConfigError` → `ConfigLoadError`
  (missing file / bad YAML) or `ConfigValidationError` (schema violation).

## 5. Domain Model

### 5.1 Document / DocumentVersion (`app/domain/models/document.py`)

- `Document` is the aggregate root. `DocumentVersion` snapshots a single
  content state; a document always has a `current_version` and retains its full
  version history.
- `add_version()` supersedes the previous version and sets `PROCESSING`;
  `mark_completed()` / `mark_failed()` transition lifecycle state. This
  enforces the single-active-version invariant at the domain level.
- `SourceMetadata` (in `app/domain/metadata/source.py`) captures provenance:
  source type, path, file name/size, MIME, SHA-256 checksum, last-modified.

### 5.2 Chunk (`app/domain/models/chunk.py`)

- `Chunk` is a content unit tied to `document_version_id`, with a running
  `chunk_index`. `ChunkType` distinguishes `PARENT` (context) from `CHILD`
  (leaf vectors); a child references `parent_chunk_id`.
- Carries `token_count` / `char_count` and an optional `embedding` vector.

### 5.3 PipelineRun (`app/domain/models/pipeline_runs.py`)

- A run-level aggregate capturing discovery/processing/skip/chunk counters,
  the embedding model used, total embedding tokens, and `estimated_cost_usd`
  for FinOps. `complete(cost_usd)` and `fail(error_msg)` transition status.

### 5.4 Repository interfaces (`app/domain/interfaces/`)

- `AbstractDocumentRepository`, `AbstractDocumentVersionRepository`,
  `AbstractChunkRepository`, `AbstractPipelineRunRepository` define the
  persistence contract consumed by application code.

## 6. Persistence (`app/db/`, `alembic/`)

- ORM mappings live in `app/db/models/`: `DocumentORM` (+ `DocumentVersionORM`
  with cascade delete-orphan), `ChunkORM`, `PipelineRunORM`. PostgreSQL
  dialect is used throughout (`UUID`, `JSONB`), with `DateTime(timezone=True)`.
- `app/db/session.py` builds the engine and `SessionLocal` from
  `configs/database.yaml` at import time and exports the `get_db()` FastAPI
  dependency. **Note:** importing this module requires the config files to be
  present and valid.
- Migrations are managed with Alembic (revisions under `alembic/versions/`).
  The lifecycle's SHA-256 dedup relies on `documents.checksum_sha256 UNIQUE`.

## 7. Ingestion (`app/ingestion/`)

The ingestion engine follows **Discover → Parse → Chunk → Embed**:

```
connectors (filesystem scan)
   └─ parsers (registry, by extension)      → ParsedDocument
        └─ chunking (registry, by strategy) → list[Chunk]
             └─ embeddings (TokenMeter)     → embedding vectors
```

- **Pipeline** (`pipeline.py`): an `IngestionPipeline` that accepts stages and
  runs them over a document. **Status: stub** — currently configured with zero
  stages; the wiring of parse/chunk/embed stages is upcoming work.
- **Connectors** (`connectors/`): `FilesystemConnector` scans a root directory
  (recursive, with exclude patterns) and yields document candidates.
- **Parsers** (`parsers/`): `BaseParser` + a class-level extension registry
  (`register_parser` / `get_parser`). Implementations: `PlainTextParser`,
  `HTMLParser`, `CSVParser`, `PDFParser`, `DOCXParser`. The PDF and DOCX
  parsers lazy-import their `pypdf` / `python-docx` dependencies and raise a
  helpful install hint when they are missing.
- **Chunking** (`chunking/`): `BaseChunker` + registry (`get_chunker`).
  `RecursiveChunker`, `TokenChunker` (sentence-aware token budget),
  `SemanticChunker` (cosine-similarity boundaries via an `Embedder` callback,
  with a token-budget fallback when no embedder is supplied), and
  `ParentChildChunker` (children linked to parents by text offset). Shared
  token estimation and sentence splitting live in `base.py`.
- **Lifecycle** (`lifecycle/`): a `VersionManager` decides an action from the
  source SHA-256 via a `ConflictResolver`: `ADD` (new document),
  `NEW_VERSION` (updated binary), `SKIP` (unchanged) or `UPDATE`. The SKIP path
  must never persist a duplicate checksum against the unique constraint.
- **Embeddings** (`embeddings/`): a `BaseEmbeddingGenerator` contract with a
  LiteLLM-backed implementation. It batches requests, retries with exponential
  backoff, and meters usage via `TokenMeter` (`request tokens`,
  `embedding tokens`, estimated cost from `PricingConfig`). The `litellm`
  package is lazy-loaded with an install hint. `get_embedding_generator()` is
  the configuration-driven factory.

## 8. Delivery Layer (`app/api/`, `ui/`)

### API (FastAPI)

- `app/api/main.py` creates the app, applies CORS middleware, and runs
  `Base.metadata.create_all(...)` on startup (note: this coexists with Alembic
  as the migration source of truth).
- Routes are mounted under `/api/v1`:
  - `/health`, `/health/live`, `/health/ready` — readiness.
  - `/ingestion/run` (POST) — creates a `PipelineRun` (persisted immediately,
    status 202), then executes the pipeline in a `BackgroundTasks` callback,
    updating the run's counters/cost on completion or failure.
  - `/ingestion/runs` (GET) — run history.
  - `/ingestion/runs/{run_id}` (GET) — poll a specific run.
- The background task opens its own `SessionLocal` so the run can be updated
  independently of the request session.

### UI (Streamlit)

- `ui/app.py` is the single page shell with sidebar navigation. Only the
  Ingestion Dashboard page is implemented (`ui/pages/ingestion.py`): it
  triggers runs via the API and polls `/ingestion/runs/{id}` to render live
  progress. Documents / Chat / FinOps / Settings are placeholders.

## 9. Not Yet Implemented (tracked in CHANGELOG.md)

The following are on the roadmap but currently exist only as scaffolds:

- `app/retrieval/` — hybrid dense+sparse search, RRF fusion, cross-encoder
  re-ranking, grounded answer generation (in progress under v0.1.11).
- `app/storage/` — pluggable object storage drivers (local / MinIO / S3);
  binary blobs are not yet stored separately from metadata.
- `app/tasks/` — dedicated async workers / scheduler.
- `app/evaluation/` — RAGAS / golden-dataset benchmarking.
- Retrieval evaluation and dashboard pages.

## 10. Testing & Tooling

- Tests live under `tests/` (currently `tests/unit/`), covering config,
  parsers, chunking, lifecycle, and embeddings. Run with `uv run pytest`.
- `ruff` enforces `E/W/F/I/UP/B/RUF` with a 120-column limit
  (`uv run ruff check app ui tests`).
- `mypy --strict` enforces typing across `app`, `ui`, and `tests`
  (`uv run mypy app ui tests`).

## 11. Design Decisions Worth Remembering

- **Three-private deps are optional:** `pypdf`, `python-docx`, and `litellm`
  are lazy-imported behind install-hint errors so the core library does not
  force heavyweight provider dependencies.
- **Config is the contract:** embedding dimensions are cross-validated against
  the pgvector index dimensions at startup to fail fast on misconfiguration.
- **Costs are measured, not guessed:** production code records provider
  `usage` token counts; `TokenMeter` falls back to a token estimator only when
  the provider does not report usage.
- **Single session ownership:** background pipeline tasks create their own DB
  session rather than reusing the request session, avoiding session reuse and
  cross-request commit hazards.