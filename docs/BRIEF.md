# Architecture Brief: Aether Wireless RAG Platform

## 1. Executive Summary

Aether Wireless is building an enterprise-grade Retrieval-Augmented Generation (RAG) platform to deliver strict, grounded answers across internal technical documentation, customer support runbooks, and network operations policies.

The platform prioritizes governance, determinism, traceability, cost accounting, and operational safety. It isolates domain logic, separates binary storage from metadata persistence, uses externalized YAML config files for runtime flexibility, and employs hybrid vector + lexical retrieval with cross-encoder re-ranking.

## 2. Core Architectural Principles

- **Clean Architecture & Domain-Driven Design (DDD):** Pure business logic inside `app/domain/` with zero dependency on FastAPI, SQLAlchemy, or external APIs.
- **Externalized Operational Configuration:** Declarative runtime parameters (models, prompts, chunking strategies, retrieval weights) live outside the application codebase in `configs/*.yaml`.
- **Immutable Document Lifecycle:** Strict versioning rules enforcing a single active version per document while preserving full historical lineage.
- **Hybrid Search Strategy:** Dense vector search (pgvector) fused with full-text keyword search (tsvector) via Reciprocal Rank Fusion (RRF) and Cross-Encoder re-ranking.
- **FinOps & Governance First:** Mandatory token metering, cost attribution per request, and pre-retrieval role/classification filtering.

## 3. High-Level System Architecture

```
+-----------------------------------------------------------------------------------------+
|                                  External Clients / UI                                  |
+-----------------------------------------------------------------------------------------+
                                             |                                             
                                             v                                             
+-----------------------------------------------------------------------------------------+
|                                     FastAPI REST API                                    |
|                     (app/api/v1 - Health, Search, Ingestion, FinOps)                    |
+-----------------------------------------------------------------------------------------+
              +------------------------------+------------------------------+              
              |                              |                              |              
              v                              v                              v              
+---------------------------+  +---------------------------+  +---------------------------+
|     Ingestion Pipeline    |  |     Retrieval Pipeline    |  |     Evaluation Engine     |
|   (Parse, Chunk, Embed)   |  |    (Dense, Sparse, RRF)   |  | (RAGAS / Golden Datasets) |
+---------------------------+  +---------------------------+  +---------------------------+
              |                              |                              |              
              +------------------------------+------------------------------+              
                                             |                                             
                                             v                                             
+-----------------------------------------------------------------------------------------+
|                               External YAML Configurations                              |
|                   (configs/ -> llm.yaml, prompts.yaml, pipelines.yaml)                  |
+-----------------------------------------------------------------------------------------+
              +------------------------------+------------------------------+              
              |                              |                              |              
              v                              v                              v              
+---------------------------+  +---------------------------+  +---------------------------+
|   PostgreSQL + pgvector   |  |    MinIO / AWS S3 Blob    |  |    OpenTelemetry / Otel   |
|  (Vectors, Tsvector, DB)  |  |    (Raw Document Store)   |  |   (Jaeger & Prometheus)   |
+---------------------------+  +---------------------------+  +---------------------------+
```

## 4. Key Subsystem Specifications

### 4.1 Configuration Management (configs/)

- **llm.yaml:** Primary/fallback chat models, embedding dimensions, temperature, resilience timeouts, and FinOps pricing rates.
- **prompts.yaml:** Versioned system prompts, grounded context templates, citation instructions, and dynamic variable schemas.
- **pipelines.yaml:** Ingestion file caps, chunking mechanics (Parent-Child, Recursive), hybrid RRF constants, and cross-encoder score thresholds.
- **database.yaml:** Connection pooling, pgvector HNSW index configurations ($m$, $ef\_construction$), and tsvector text search language dictionaries.

### 4.2 Data Storage Layer

- **Binary Documents:** Managed via pluggable Object Storage drivers (LocalStorage, MinIOStorage, S3Storage).
- **Relational & Vector Data:** PostgreSQL equipped with pgvector for dense vectors (1536d HNSW), native tsvector generated columns for full-text keyword search, and JSONB for lineage/metadata tracking.

### 4.3 Ingestion & Lineage Pipeline

- **Incremental Ingestion:** SHA-256 binary hash checks skip unaltered uploads.
- **Version Control:** Automates V1 initializations and auto-increments modified binaries, enforcing single-active-version constraints.
- **Parent-Child Chunking:** Stores fine-grained child chunks for precise vector matches while linking to larger parent contexts for LLM generation.

### 4.4 Hybrid Retrieval & Answer Generation

- **Hybrid Search:** Dense and Sparse search queries execute concurrently.
- **Reciprocal Rank Fusion (RRF):** Merges dense and lexical rank lists using:

$$
RRF\_Score(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}
$$

- **Re-Ranking:** Cross-Encoder models rescore candidate chunks before context assembly.
- **Grounded Generation:** Enforces strict system prompts from `prompts.yaml` requiring verifiable inline citations.

## Directory Structure

```
aether-rag/
├── .github/                           # CI/CD Workflows
│   └── workflows/
│       ├── ci.yml                     # Linting, type checks, pytest, security scanning
│       └── cd.yml                     # Docker builds & deployment pipeline
│
├── alembic/                           # Database Migration Management
│   ├── versions/                      # Schema migration scripts
│   ├── env.py                         # Alembic environment context
│   └── script.py.mako
│
├── configs/                           # External Operational Configuration (YAML)
│   ├── llm.yaml                       # LLM providers, embedding models, pricing rates
│   ├── prompts.yaml                   # Versioned system prompts & grounding rules
│   ├── pipelines.yaml                 # Ingestion, chunking, RRF & re-ranking settings
│   └── database.yaml                  # Vector index settings & connection parameters
│
├── app/                               # Application Core Source Code
│   ├── api/                           # Delivery Layer (FastAPI REST Controllers)
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── health.py          # Liveness & Readiness endpoints
│   │   │   │   └── ingestion.py       # Trigger document ingestion jobs
│   │   │   ├── dependencies.py        # DB sessions, Auth, OTel context injection
│   │   │   └── router.py              # API Router aggregation
│   │   └── main.py                    # FastAPI application factory & OTel middleware
│   │
│   ├── core/                          # Cross-Cutting Infrastructure Concerns
│   │   ├── config.py                  # Pydantic-Settings (ENV management)
│   │   └── logging.py                 # Structured JSON logging with trace correlation IDs
│   │
│   ├── domain/                        # Pure Domain Logic (No DB/Framework dependencies)
│   │   ├── models/                    # Core Entities (Document, Version, Chunk, Answer)
│   │   ├── metadata/                  # Lineage, Governance, Source & Cost Metadata
│   │   └── interfaces/                # Repositories & Storage ABC abstractions
│   │
│   ├── db/                            # Database Infrastructure
│   │   ├── models/                    # SQLAlchemy ORM mappings (vector, tsvector)
│   │   ├── repositories/              # Concrete DB repositories implementing interfaces
│   │   └── session.py                 # Engine config & SessionLocal factory
│   │
│   ├── storage/                       # Object Storage Drivers
│   │   ├── base.py                    # Storage ABC Driver Contract
│   │   ├── local_storage.py           # Local dev driver
│   │   ├── minio_storage.py           # Local S3-compatible driver
│   │   └── s3_storage.py              # AWS S3 production driver
│   │
│   ├── tasks/                         # Asynchronous Workers
│   │   ├── ingestion_task.py          # Background ingestion job handling
│   │   ├── evaluation_task.py         # Background evaluation benchmark runs
│   │   └── scheduler.py               # Scheduled tasks and cleanup
│   │
│   ├── ingestion/                     # Ingestion Core Engine
│   │   ├── pipeline.py                # Ingestion Orchestrator
│   │   ├── connectors/                # Multi-source connectors (Filesystem, API, DB)
│   │   ├── parsers/                   # Document layout parsers (PDF, DOCX, HTML, CSV)
│   │   ├── lifecycle/                 # Version manager & SHA-256 conflict resolver
│   │   ├── chunking/                  # Recursive, Semantic, and Parent-Child splitters
│   │   └── embeddings/                # LiteLLM Embedding Generator
│   │
│   ├── retrieval/                     # Hybrid Retrieval & Answer Generation Core
│   │   ├── pipeline.py                # Retrieval Orchestrator (OTel Traced)
│   │   ├── retrievers/                # Search Engines
│   │   │   ├── dense.py               # pgvector similarity search
│   │   │   ├── sparse.py              # PostgreSQL full-text search (tsvector/tsquery)
│   │   │   ├── hybrid.py              # Unified dense + sparse execution engine
│   │   │   └── rrf.py                 # Reciprocal Rank Fusion calculation
│   │   ├── rerankers/                 # Cross-Encoder Re-Rankers
│   │   │   └── cross_encoder.py       # Cross-Encoder re-ranker integration
│   │   │
│   │
│   └── evaluation/                    # Quality Benchmarking Pipeline
│       ├── pipeline.py                # Evaluation Orchestrator
│       ├── metrics/                   # Retrieval (Recall@K, MRR) & Generation metrics
│       └── datasets/                  # Versioned Golden Dataset managers
│
├── ui/                                # Streamlit Dashboard Interface
│   ├── app.py                         # Streamlit entry point
│   ├── pages/                         # Chat, Documents, Prompts, FinOps, Evaluation
│   └── components/                    # Dashboard visual widgets
│
├── tests/                             # Test Suite
│   ├── conftest.py                    # Pytest fixtures & Testcontainers setup
│   ├── unit/                          # Domain models, chunker, & RRF unit tests
│   ├── integration/                   # Repository, DB, & S3 storage driver tests
│   └── e2e/                           # Full pipeline end-to-end tests
│
├── docs/                              # Architecture Decision Records (ADRs)
├── docker-compose.yml                 # Local Infrastructure Stack (DB, MinIO, Otel, Jaeger)
├── Dockerfile                         # Production Multi-Stage Dockerfile
├── alembic.ini                        # Alembic DB migration config
├── pyproject.toml                     # Dependencies, uv, ruff, mypy, pytest configs
├── .env.example                       # Environment variables template
├── BRIEF.md                           # Master Architecture Blueprint
├── CHANGELOG.md                       # Versioned Execution Roadmap
├── README.md                          # Quickstart guide
└── LICENSE
```