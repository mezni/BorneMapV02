"""Integration tests for dense, sparse, and hybrid retrieval against Postgres.

These tests auto-skip when PostgreSQL is unreachable or the ``vector``
extension is not installed. Every test runs inside a transaction that is
rolled back, so no seed data persists.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from app.db.session import SessionLocal
from app.retrieval.retrievers import DenseRetriever, HybridRetriever, SparseRetriever
from sqlalchemy import text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

DIMS = 1536
DOC_A = uuid4()
DOC_B = uuid4()
VER_A = uuid4()
VER_B = uuid4()


@pytest.fixture()
def db_session() -> Iterator[Session]:
    try:
        session = SessionLocal()
    except Exception:
        pytest.skip("Could not create a database session")
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def pgvector_enabled(db_session: Session) -> bool:
    try:
        row = db_session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).fetchone()
    except Exception:
        pytest.skip("PostgreSQL is not reachable")
    if not row or not row[0]:
        pytest.skip("pgvector extension is not installed")
    db_session.rollback()
    return True


def _vector(*first: float) -> str:
    """Render a 1536-dim pgvector literal with the given leading values."""
    out = [0.0] * DIMS
    for i, value in enumerate(first):
        out[i] = float(value)
    return "[" + ",".join(str(value) for value in out) + "]"


def _seed_document(session: Session, document_id: Any, checksum: str) -> None:
    session.execute(
        text(
            """
            INSERT INTO documents
                (id, title, source_type, source_path, file_name, file_extension,
                 file_size_bytes, checksum_sha256, status, metadata, created_at, updated_at)
            VALUES
                (:id, 'seed', 'FILESYSTEM', '', '', '', 0,
                 :checksum, 'COMPLETED', '{}'::jsonb, now(), now())
            """
        ),
        {"id": document_id, "checksum": checksum},
    )


def _seed_version(session: Session, version_id: Any, document_id: Any, content_hash: str) -> None:
    session.execute(
        text(
            """
            INSERT INTO document_versions
                (id, document_id, version_number, content_hash, status, chunk_count,
                 total_tokens, source_path, file_name, file_extension, file_size_bytes,
                 mime_type, checksum_sha256, last_modified, error_message, created_at, processed_at)
            VALUES
                (:id, :document_id, 1, :content_hash, 'ACTIVE', 0, 0,
                 '', '', '', 0, NULL, '', NULL, NULL, now(), NULL)
            """
        ),
        {"id": version_id, "document_id": document_id, "content_hash": content_hash},
    )


def _seed_chunk(
    session: Session,
    *,
    chunk_id: Any,
    document_id: Any,
    version_id: Any,
    chunk_index: int,
    content: str,
    vector: str | None = None,
) -> None:
    embedding = "NULL" if vector is None else "CAST(:embedding AS vector(1536))"
    params: dict[str, Any] = {
        "id": chunk_id,
        "document_id": document_id,
        "version_id": version_id,
        "chunk_index": chunk_index,
        "content": content,
        "char_count": len(content),
    }
    if vector is not None:
        params["embedding"] = vector
    session.execute(
        text(
            f"""
            INSERT INTO chunks
                (id, document_id, document_version_id, chunk_index, chunk_type,
                 parent_chunk_id, content, token_count, char_count, embedding,
                 metadata, created_at)
            VALUES
                (:id, :document_id, :version_id, :chunk_index, 'PARENT',
                 NULL, :content, 3, :char_count, {embedding},
                 '{{}}'::jsonb, now())
            """
        ),
        params,
    )


def _seed_pair(session: Session, *, content_a: str, content_b: str, vec_a: str, vec_b: str) -> None:
    _seed_document(session, DOC_A, f"checksum-a-{uuid4()}")
    _seed_document(session, DOC_B, f"checksum-b-{uuid4()}")
    _seed_version(session, VER_A, DOC_A, "hash-a")
    _seed_version(session, VER_B, DOC_B, "hash-b")
    _seed_chunk(
        session,
        chunk_id=uuid4(),
        document_id=DOC_A,
        version_id=VER_A,
        chunk_index=0,
        content=content_a,
        vector=vec_a,
    )
    _seed_chunk(
        session,
        chunk_id=uuid4(),
        document_id=DOC_B,
        version_id=VER_B,
        chunk_index=0,
        content=content_b,
        vector=vec_b,
    )


def test_sparse_full_text_search_roundtrip(db_session: Session, pgvector_enabled: bool) -> None:
    db_session.begin()
    try:
        _seed_pair(
            db_session,
            content_a="radio access network resilience runbook",
            content_b="enterprise billing procedures for wireless customers",
            vec_a=_vector(1.0),
            vec_b=_vector(0.0, 1.0),
        )
        retriever = SparseRetriever(db_session)
        results = retriever.retrieve("billing", top_k=5)
        assert results, "expected at least one full-text match"
        assert "billing" in results[0].content
    finally:
        db_session.rollback()


def test_dense_vector_search_roundtrip(db_session: Session, pgvector_enabled: bool) -> None:
    db_session.begin()
    try:
        _seed_pair(
            db_session,
            content_a="radio access network resilience runbook",
            content_b="enterprise billing procedures for wireless customers",
            vec_a=_vector(1.0),
            vec_b=_vector(0.0, 1.0),
        )
        query_vector = [float(x) for x in _vector(1.0).strip("[]").split(",")]
        retriever = DenseRetriever(db_session, embed_query=lambda query: query_vector)
        results = retriever.retrieve("any query", top_k=5)
        assert results, "expected at least one dense match"
        assert results[0].content == "radio access network resilience runbook"
        assert round(results[0].score, 5) == 1.0
    finally:
        db_session.rollback()


def test_hybrid_fusion_roundtrip(db_session: Session, pgvector_enabled: bool) -> None:
    db_session.begin()
    try:
        _seed_pair(
            db_session,
            content_a="radio access network resilience runbook",
            content_b="enterprise billing procedures for wireless customers",
            vec_a=_vector(1.0),
            vec_b=_vector(0.0, 1.0),
        )
        query_vector = [float(x) for x in _vector(1.0).strip("[]").split(",")]
        dense = DenseRetriever(db_session, embed_query=lambda query: query_vector)
        sparse = SparseRetriever(db_session)
        hybrid = HybridRetriever(db_session, dense=dense, sparse=sparse)
        results = hybrid.retrieve("radio billing", top_k=5)
        ids = [r.chunk_id for r in results]
        assert len(ids) == 2
        assert results[0].content == "radio access network resilience runbook"
    finally:
        db_session.rollback()
