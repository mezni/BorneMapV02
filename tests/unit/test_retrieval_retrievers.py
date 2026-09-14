"""Unit tests for the retrieval search engine modules."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from typing import Any, cast
from uuid import UUID

import pytest
from app.core.config import DenseRetrievalConfig, HybridRetrievalConfig, SparseRetrievalConfig
from app.retrieval.retrievers import (
    DenseRetriever,
    HybridRetriever,
    RetrievedChunk,
    SparseRetriever,
    reciprocal_rank_fusion,
)
from sqlalchemy.orm import Session

ID_Q1 = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ID_Q2 = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ID_Q3 = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _make_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": ID_Q1,
        "document_id": UUID("22222222-2222-2222-2222-222222222222"),
        "document_version_id": UUID("33333333-3333-3333-3333-333333333333"),
        "chunk_index": 0,
        "chunk_type": "PARENT",
        "content": "some chunk content",
        "token_count": 4,
        "char_count": 18,
        "metadata": {"section": "a"},
        "score": 0.5,
    }
    row.update(overrides)
    return row


def _chunk(**overrides: Any) -> RetrievedChunk:
    base: dict[str, Any] = {
        "chunk_id": ID_Q1,
        "document_id": UUID("22222222-2222-2222-2222-222222222222"),
        "document_version_id": UUID("33333333-3333-3333-3333-333333333333"),
        "chunk_index": 0,
        "chunk_type": "PARENT",
        "content": "some chunk content",
        "token_count": 4,
        "char_count": 18,
        "metadata": {"section": "a"},
        "score": 0.5,
    }
    base.update(overrides)
    return RetrievedChunk(**base)


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)


class StubSession:
    """Session double that records executed statements and returns canned rows."""

    def __init__(self, rows: list[dict[str, Any]] | None = None, *, in_transaction: bool = False) -> None:
        self._rows = rows or []
        self._in_transaction = in_transaction
        self.executed: list[tuple[str, dict[str, Any]]] = []
        self.begin_calls = 0

    def in_transaction(self) -> bool:
        return self._in_transaction

    @contextmanager
    def begin(self) -> Any:
        self.begin_calls += 1
        yield

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = str(statement)
        self.executed.append((sql, params or {}))
        if "chunks" in sql:
            return _FakeResult(self._rows)
        return _FakeResult([])

    def statements(self, needle: str) -> list[str]:
        return [sql for sql, _ in self.executed if needle in sql]

    def params(self, needle: str) -> list[dict[str, Any]]:
        return [params for sql, params in self.executed if needle in sql]


def _stub(rows: list[dict[str, Any]] | None = None, *, in_transaction: bool = False) -> tuple[StubSession, Session]:
    stub = StubSession(rows, in_transaction=in_transaction)
    return stub, cast("Session", stub)


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def test_rrf_fuses_ranked_lists() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "d", "a"]], k=60)
    assert [item for item, _ in fused] == ["b", "a", "d", "c"]
    assert abs(dict(fused)["b"] - (1 / 61 + 1 / 62)) < 1e-9


def test_rrf_deduplicates_items_across_lists() -> None:
    fused = reciprocal_rank_fusion([["a", "b"], ["a", "c"]], k=60)
    items = [item for item, _ in fused]
    assert items.count("a") == 1
    assert items[0] == "a"


def test_rrf_weights_scale_list_contribution() -> None:
    fused = reciprocal_rank_fusion([["a"], ["b"]], k=60, weights=[1.0, 100.0])
    assert [item for item, _ in fused] == ["b", "a"]


def test_rrf_empty_input() -> None:
    assert reciprocal_rank_fusion([]) == []


def test_rrf_weight_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="weights"):
        reciprocal_rank_fusion([["a"], ["b"]], weights=[1.0])


# ---------------------------------------------------------------------------
# Dense retriever
# ---------------------------------------------------------------------------


def test_dense_formats_vector_literal() -> None:
    _, session = _stub()
    retriever = DenseRetriever(session, embed_query=lambda query: [])
    assert retriever._format_vector([0.5, -1.0, 2.0]) == "[0.5,-1.0,2.0]"


def test_dense_retrieve_maps_and_scores_rows() -> None:
    _, session = _stub([_make_row(score="0.75")])
    retriever = DenseRetriever(session, embed_query=lambda query: [0.1, 0.2, 0.3])
    results = retriever.retrieve("hello", top_k=5)
    assert len(results) == 1
    chunk = results[0]
    assert chunk.chunk_id == ID_Q1
    assert chunk.score == 0.75
    assert chunk.content == "some chunk content"
    assert chunk.metadata == {"section": "a"}


def test_dense_executes_set_local_then_query() -> None:
    stub, session = _stub([_make_row()])
    retriever = DenseRetriever(session, embed_query=lambda query: [0.1, 0.2, 0.3])
    retriever.retrieve("hello", top_k=5)
    assert stub.statements("ef_search") == ["SET LOCAL hnsw.ef_search = :ef_search"]
    params = stub.params("chunks")[0]
    assert params["qvec"] == "[0.1,0.2,0.3]"
    assert params["top_k"] == 5
    assert "<=>" in stub.statements("chunks")[0]
    assert "LIMIT :top_k" in stub.statements("chunks")[0]


def test_dense_empty_query_vector_returns_empty() -> None:
    stub, session = _stub([_make_row()])
    retriever = DenseRetriever(session, embed_query=lambda query: [])
    assert retriever.retrieve("anything") == []
    assert stub.statements("chunks") == []


def test_dense_default_top_k_and_ef_from_config() -> None:
    stub, session = _stub([_make_row()])
    retriever = DenseRetriever(
        session,
        embed_query=lambda query: [1.0],
        config=DenseRetrievalConfig(top_k=7, ef_search=12),
    )
    retriever.retrieve("q")
    assert stub.params("chunks")[0]["top_k"] == 7
    assert stub.params("ef_search") == [{"ef_search": 12}]


def test_dense_reuses_caller_transaction() -> None:
    stub, session = _stub([_make_row()], in_transaction=True)
    retriever = DenseRetriever(session, embed_query=lambda query: [1.0])
    retriever.retrieve("q")
    assert stub.begin_calls == 0
    assert len(stub.executed) == 2


def test_dense_opens_own_transaction_when_idle() -> None:
    stub, session = _stub([_make_row()])
    retriever = DenseRetriever(session, embed_query=lambda query: [1.0])
    retriever.retrieve("q")
    assert stub.begin_calls == 1


# ---------------------------------------------------------------------------
# Sparse retriever
# ---------------------------------------------------------------------------


def test_sparse_empty_query_returns_empty() -> None:
    _, session = _stub([])
    retriever = SparseRetriever(session)
    assert retriever.retrieve("") == []
    assert retriever.retrieve("   ") == []


def test_sparse_retrieve_maps_and_scores_rows() -> None:
    _, session = _stub([_make_row(content="network runbook", score="0.9")])
    retriever = SparseRetriever(session, config=SparseRetrievalConfig(top_k=3))
    results = retriever.retrieve("network 5G", top_k=3)
    assert len(results) == 1
    assert results[0].content == "network runbook"
    assert results[0].score == 0.9


def test_sparse_builds_tsquery_and_ranks() -> None:
    stub, session = _stub([_make_row()])
    retriever = SparseRetriever(session, config=SparseRetrievalConfig(top_k=3))
    retriever.retrieve("network 5G", top_k=3)
    sql = stub.statements("chunks")[0]
    assert "search_vector" in sql
    assert "websearch_to_tsquery" in sql
    assert "ts_rank" in sql
    params = stub.params("chunks")[0]
    assert params["query"] == "network 5G"
    assert params["language"] == "english"
    assert params["top_k"] == 3


def test_sparse_default_top_k_from_config() -> None:
    stub, session = _stub([_make_row()])
    retriever = SparseRetriever(session, config=SparseRetrievalConfig(top_k=9))
    retriever.retrieve("query word")
    assert stub.params("chunks")[0]["top_k"] == 9


# ---------------------------------------------------------------------------
# Hybrid retriever
# ---------------------------------------------------------------------------


def _hybrid(
    dense_rows: list[dict[str, Any]],
    sparse_rows: list[dict[str, Any]],
    *,
    config: HybridRetrievalConfig | None = None,
) -> tuple[HybridRetriever, StubSession, StubSession]:
    dense_stub, dense_session = _stub(dense_rows)
    sparse_stub, sparse_session = _stub(sparse_rows)
    dense = DenseRetriever(dense_session, embed_query=lambda query: [1.0])
    sparse = SparseRetriever(sparse_session)
    hybrid = HybridRetriever(_stub()[1], dense=dense, sparse=sparse, config=config)
    return hybrid, dense_stub, sparse_stub


def test_hybrid_fuses_dense_and_sparse() -> None:
    dense_rows = [_make_row(id=ID_Q1, score="0.9"), _make_row(id=ID_Q2, chunk_index=1, score="0.5")]
    sparse_rows = [_make_row(id=ID_Q2, chunk_index=1, score="0.8"), _make_row(id=ID_Q3, chunk_index=2, score="0.6")]
    hybrid, _, _ = _hybrid(dense_rows, sparse_rows)
    results = hybrid.retrieve("query", top_k=2)
    assert [r.chunk_id for r in results] == [ID_Q2, ID_Q1]
    assert abs(results[0].score - (1 / 61 + 1 / 62)) < 1e-9


def test_hybrid_queries_candidate_k_from_both_retrievers() -> None:
    hybrid, dense_stub, sparse_stub = _hybrid(
        [_make_row()],
        [_make_row(id=ID_Q2, chunk_index=1)],
        config=HybridRetrievalConfig(candidate_k=17, rrf_k=60, dense_weight=1.0, sparse_weight=1.0),
    )
    hybrid.retrieve("query")
    assert dense_stub.params("chunks")[0]["top_k"] == 17
    assert sparse_stub.params("chunks")[0]["top_k"] == 17


def test_hybrid_default_top_k_is_candidate_k() -> None:
    dense_rows = [_make_row(id=ID_Q1), _make_row(id=ID_Q2, chunk_index=1)]
    sparse_rows = [_make_row(id=ID_Q3, chunk_index=2)]
    hybrid, _, _ = _hybrid(dense_rows, sparse_rows, config=HybridRetrievalConfig(candidate_k=3))
    results = hybrid.retrieve("query")
    assert len(results) == 3


def test_hybrid_empty_results() -> None:
    hybrid, _, _ = _hybrid([], [])
    assert hybrid.retrieve("query") == []


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


def test_retrieved_chunk_is_frozen() -> None:
    chunk = _chunk()
    with pytest.raises(FrozenInstanceError):
        chunk.score = 2.0  # type: ignore[misc]
