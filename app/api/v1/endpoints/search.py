"""Hybrid retrieval and chat endpoints.

Wire the retrieval orchestrator (dense + sparse + RRF fusion + cross-encoder
re-ranking) to the API layer. The chat endpoint assembles a grounded
:class:`Answer` from the top results; answer generation itself lands with the
answer stage.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.search import ChatRequest, ChatResponse, SearchRequest, SearchResponse, SearchResultItem
from app.core.config import RuntimeConfig, load_runtime_config
from app.db.session import get_db
from app.domain.models.answer import Answer, AnswerStatus
from app.ingestion.embeddings import get_embedding_generator
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.rerankers import CrossEncoderReRanker
from app.retrieval.retrievers import RetrievedChunk
from app.retrieval.retrievers.dense import DenseRetriever
from app.retrieval.retrievers.sparse import SparseRetriever

router = APIRouter(tags=["search"])


def _build_pipeline(db: Session, config: RuntimeConfig) -> RetrievalPipeline:
    generator = get_embedding_generator(
        config.llm.embeddings,
        timeouts=config.llm.timeouts,
        pricing=config.llm.pricing,
    )
    dense = DenseRetriever(
        db,
        embed_query=lambda query: generator.embed_texts([query]).embeddings[0],
    )
    sparse = SparseRetriever(db)
    reranker = CrossEncoderReRanker(config.pipelines.retrieval.rerank)
    return RetrievalPipeline(
        db,
        dense=dense,
        sparse=sparse,
        reranker=reranker,
        config=config.pipelines.retrieval,
    )


DBSession = Annotated[Session, Depends(get_db)]


def get_pipeline(db: DBSession) -> RetrievalPipeline:
    """Build the retrieval orchestrator from runtime config for a request."""
    config = load_runtime_config()
    return _build_pipeline(db, config)


def _to_result(chunk: RetrievedChunk) -> SearchResultItem:
    return SearchResultItem(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        document_version_id=chunk.document_version_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        score=chunk.score,
        metadata=chunk.metadata,
    )


def _build_answer(query: str, results: Sequence[RetrievedChunk], config: RuntimeConfig) -> Answer:
    model = config.llm.chat.primary.model
    if not results:
        return Answer(query=query, status=AnswerStatus.NO_CONTEXT, model=model)
    return Answer(
        query=query,
        source_chunk_ids=[chunk.chunk_id for chunk in results],
        status=AnswerStatus.GENERATED,
        model=model,
        metadata={"result_count": len(results)},
    )


@router.post("/search", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    pipeline: Annotated[RetrievalPipeline, Depends(get_pipeline)],
) -> SearchResponse:
    """Run hybrid retrieval (dense + sparse + RRF) with cross-encoder re-ranking."""
    results = pipeline.retrieve(payload.query, top_k=payload.top_k)
    return SearchResponse(query=payload.query, results=[_to_result(chunk) for chunk in results])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, pipeline: Annotated[RetrievalPipeline, Depends(get_pipeline)]) -> ChatResponse:
    """Retrieve context for ``query`` and assemble a grounded answer."""
    config = load_runtime_config()
    results = pipeline.retrieve(payload.query, top_k=payload.top_k)
    answer = _build_answer(payload.query, results, config)
    return ChatResponse(
        query=answer.query,
        answer_text=answer.answer_text,
        status=answer.status.value,
        source_chunk_ids=answer.source_chunk_ids,
        model=answer.model,
    )
