"""Unit tests for the retrieval orchestrator and cross-encoder re-ranker."""

from __future__ import annotations

from typing import cast
from uuid import UUID

import pytest
from app.core.config import (
    DenseRetrievalConfig,
    HybridRetrievalConfig,
    RerankerConfig,
    RetrievalConfig,
    SparseRetrievalConfig,
)
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.rerankers import CrossEncoderReRanker
from app.retrieval.retrievers import RetrievedChunk
from app.retrieval.retrievers.dense import DenseRetriever
from app.retrieval.retrievers.sparse import SparseRetriever

ID_Q1 = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ID_Q2 = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ID_Q3 = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _chunk(chunk_id: UUID, *, index: int = 0, content: str = "some chunk content") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=UUID("22222222-2222-2222-2222-222222222222"),
        document_version_id=UUID("33333333-3333-3333-3333-333333333333"),
        chunk_index=index,
        chunk_type="PARENT",
        content=content,
        token_count=4,
        char_count=len(content),
        metadata={"section": "a"},
        score=0.5,
    )


def _rerank_config(*, enabled: bool = True, top_k: int = 5, threshold: float = 0.5) -> RerankerConfig:
    return RerankerConfig(
        enabled=enabled,
        model="cross_encoder/ms-marco-MiniLM-L-6-v2",
        top_k=top_k,
        score_threshold=threshold,
    )


# ---------------------------------------------------------------------------
# Cross-Encoder re-ranker
# ---------------------------------------------------------------------------


def test_cross_encoder_rerank_sorts_by_injected_scores() -> None:
    reranker = CrossEncoderReRanker(_rerank_config(top_k=2), score_pairs=lambda pairs: [3.0, 1.0, 2.0])
    chunks = [_chunk(ID_Q1), _chunk(ID_Q2, index=1), _chunk(ID_Q3, index=2)]
    ranked = reranker.rerank("query", chunks)
    assert [c.chunk_id for c in ranked] == [ID_Q1, ID_Q3]
    assert ranked[0].score == 3.0


def test_cross_encoder_rerank_filters_by_threshold() -> None:
    reranker = CrossEncoderReRanker(_rerank_config(threshold=0.7), score_pairs=lambda pairs: [0.9, 0.4, 0.7])
    chunks = [_chunk(ID_Q1), _chunk(ID_Q2, index=1), _chunk(ID_Q3, index=2)]
    ranked = reranker.rerank("query", chunks)
    assert [c.chunk_id for c in ranked] == [ID_Q1, ID_Q3]


def test_cross_encoder_rerank_explicit_threshold_overrides_config() -> None:
    reranker = CrossEncoderReRanker(_rerank_config(threshold=0.9), score_pairs=lambda pairs: [0.9, 0.4, 0.7])
    chunks = [_chunk(ID_Q1), _chunk(ID_Q2, index=1), _chunk(ID_Q3, index=2)]
    ranked = reranker.rerank("query", chunks, score_threshold=0.1)
    assert [c.chunk_id for c in ranked] == [ID_Q1, ID_Q3, ID_Q2]


def test_cross_encoder_rerank_default_top_k_from_config() -> None:
    reranker = CrossEncoderReRanker(_rerank_config(top_k=2), score_pairs=lambda pairs: [3.0, 1.0, 2.0])
    chunks = [_chunk(ID_Q1), _chunk(ID_Q2, index=1), _chunk(ID_Q3, index=2)]
    assert len(reranker.rerank("query", chunks)) == 2


def test_cross_encoder_rerank_disabled_preserves_order() -> None:
    reranker = CrossEncoderReRanker(_rerank_config(enabled=False), score_pairs=lambda pairs: [3.0, 1.0, 2.0])
    chunks = [_chunk(ID_Q1), _chunk(ID_Q2, index=1), _chunk(ID_Q3, index=2)]
    ranked = reranker.rerank("query", chunks)
    assert [c.chunk_id for c in ranked] == [ID_Q1, ID_Q2, ID_Q3]


def test_cross_encoder_rerank_model_less_passes_through() -> None:
    reranker = CrossEncoderReRanker(_rerank_config())
    chunks = [_chunk(ID_Q3, index=2), _chunk(ID_Q1)]
    ranked = reranker.rerank("query", chunks)
    assert [c.chunk_id for c in ranked] == [ID_Q3, ID_Q1]


def test_cross_encoder_rerank_score_mismatch_raises() -> None:
    reranker = CrossEncoderReRanker(_rerank_config(), score_pairs=lambda pairs: [1.0])
    with pytest.raises(ValueError, match="scores"):
        reranker.rerank("query", [_chunk(ID_Q1), _chunk(ID_Q2, index=1)])


def test_cross_encoder_rerank_empty_results() -> None:
    reranker = CrossEncoderReRanker(_rerank_config())
    assert reranker.rerank("query", []) == []


# ---------------------------------------------------------------------------
# Retrieval orchestration pipeline
# ---------------------------------------------------------------------------


class _StubRetriever:
    def __init__(self, results: list[RetrievedChunk]) -> None:
        self._results = results
        self.last_top_k: int | None = None

    def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        self.last_top_k = top_k
        return self._results


def _pipeline_config(candidate_k: int = 100) -> RetrievalConfig:
    return RetrievalConfig(
        dense=DenseRetrievalConfig(top_k=20, ef_search=40),
        sparse=SparseRetrievalConfig(top_k=20),
        hybrid=HybridRetrievalConfig(rrf_k=60, dense_weight=1.0, sparse_weight=1.0, candidate_k=candidate_k),
        rerank=_rerank_config(enabled=False),
    )


def _pipeline(
    dense_results: list[RetrievedChunk],
    sparse_results: list[RetrievedChunk],
    *,
    reranker: CrossEncoderReRanker | None = None,
    candidate_k: int = 100,
) -> tuple[RetrievalPipeline, _StubRetriever, _StubRetriever]:
    dense_stub = _StubRetriever(dense_results)
    sparse_stub = _StubRetriever(sparse_results)
    pipeline = RetrievalPipeline(
        None,  # type: ignore[arg-type]  # retrievers are stubs; pipeline never opens a Session
        dense=cast("DenseRetriever", dense_stub),
        sparse=cast("SparseRetriever", sparse_stub),
        reranker=reranker,
        config=_pipeline_config(candidate_k=candidate_k),
    )
    return pipeline, dense_stub, sparse_stub


def test_pipeline_fuses_dense_and_sparse() -> None:
    dense_rows = [_chunk(ID_Q1), _chunk(ID_Q2, index=1)]
    sparse_rows = [_chunk(ID_Q2, index=1), _chunk(ID_Q3, index=2)]
    pipeline, _, _ = _pipeline(dense_rows, sparse_rows)
    results = pipeline.retrieve("query", top_k=2)
    assert [r.chunk_id for r in results] == [ID_Q2, ID_Q1]
    assert len(results) == 2


def test_pipeline_queries_candidate_k_before_trimming() -> None:
    pipeline, dense_stub, sparse_stub = _pipeline([_chunk(ID_Q1)], [_chunk(ID_Q2, index=1)], candidate_k=17)
    pipeline.retrieve("query", top_k=1)
    assert dense_stub.last_top_k == 17
    assert sparse_stub.last_top_k == 17


def test_pipeline_without_reranker_returns_candidates() -> None:
    pipeline, _, _ = _pipeline([_chunk(ID_Q1)], [_chunk(ID_Q2, index=1)])
    results = pipeline.retrieve("query")
    assert {r.chunk_id for r in results} == {ID_Q1, ID_Q2}


def test_pipeline_reranks_when_reranker_present() -> None:
    chunks = [_chunk(ID_Q1), _chunk(ID_Q2, index=1), _chunk(ID_Q3, index=2)]
    reranker = CrossEncoderReRanker(_rerank_config(), score_pairs=lambda pairs: [3.0, 1.0, 2.0])
    pipeline, _, _ = _pipeline(chunks, [], reranker=reranker)
    results = pipeline.retrieve("query", top_k=2)
    assert [r.chunk_id for r in results] == [ID_Q1, ID_Q3]
    assert results[0].score == 3.0


def test_pipeline_empty_query_returns_empty() -> None:
    pipeline, _, _ = _pipeline([], [])
    assert pipeline.retrieve("query") == []


def test_pipeline_rerank_applies_config_threshold() -> None:
    chunks = [_chunk(ID_Q1), _chunk(ID_Q2, index=1), _chunk(ID_Q3, index=2)]
    reranker = CrossEncoderReRanker(_rerank_config(threshold=0.7), score_pairs=lambda pairs: [0.9, 0.4, 0.7])
    pipeline, _, _ = _pipeline(chunks, [], reranker=reranker)
    results = pipeline.retrieve("query")
    assert [r.chunk_id for r in results] == [ID_Q1, ID_Q3]
