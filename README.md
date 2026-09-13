# Aether Wireless Enterprise RAG Platform

Production-grade, highly observable RAG platform designed following Clean Architecture, Domain-Driven Design (DDD), Hybrid Vector Search, and FinOps Token Accounting.

## Key Features

- **Externalized Operational Configurations:** Operational settings (LLMs, Prompts, Chunking strategies, Hybrid weights) managed via declarative YAML files in `configs/`.
- **Clean Architecture & DDD:** Strict boundary enforcement between domain business rules, database drivers, and FastAPI presentation layers.
- **Hybrid Search Engine:** Combines pgvector dense vector similarity with PostgreSQL tsvector full-text search using Reciprocal Rank Fusion (RRF) and Cross-Encoder re-ranking.
- **Document Lineage & Lifecycle:** SHA-256 duplicate detection, immutable document versioning, and single-active-version state enforcement.
- **FinOps Token Accounting:** Automatic metering of embedding/LLM usage with real-time USD cost calculation and department attribution.
- **Full Observability:** OpenTelemetry distributed tracing, Prometheus performance metrics, and structured JSON logging with correlation IDs.

## Directory Architecture Overview

```
aether-rag/
├── configs/          # External operational YAML configs (llm, prompts, pipelines, db)
├── app/              # Clean Architecture backend (api, core, domain, db, ingestion, retrieval)
├── ui/               # Streamlit chat & operations dashboard
├── alembic/          # Database schema migrations
├── tests/            # Unit, integration, and E2E testing framework
└── docker-compose.yml # Local development stack
```

## Quickstart Guide

### 1. Prerequisites

- Python: 3.12+
- Package Manager: `uv`
- Container Engine: Docker & Docker Compose

### 2. Environment Setup

```bash
# Clone the repository
git clone https://github.com/organization/aether-rag.git
cd aether-rag

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv sync

# Setup environment file
cp .env.example .env
```

### 3. Spin Up Local Infrastructure Stack

Start PostgreSQL (pgvector), MinIO object storage, Prometheus, and Jaeger:

```bash
docker compose up -d
```

### 4. Execute Schema Migrations

```bash
uv run alembic upgrade head
```

### 5. Launch Application

```bash
# Start FastAPI Backend Engine
uv run uvicorn app.api.main:app --reload --port 8000

# Start Streamlit Frontend (In a separate terminal)
uv run streamlit run ui/app.py
```

Access the API documentation at http://localhost:8000/docs and the Streamlit dashboard at http://localhost:8501.

## Configuration Management

All operational parameters can be updated directly in the `configs/` directory without requiring code re-compilation:

- **configs/llm.yaml:** Update model choices, temperature settings, and pricing rates.
- **configs/prompts.yaml:** Edit grounded answer templates and system prompt rules.
- **configs/pipelines.yaml:** Adjust chunking window sizes, RRF fusion constant $k$, and re-ranking thresholds.
- **configs/database.yaml:** Configure HNSW index parameters ($m$, $ef\_construction$).