"""API request/response schemas for hybrid retrieval & chat endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, gt=0)


class SearchResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: UUID
    document_id: UUID
    document_version_id: UUID
    chunk_index: int
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    results: list[SearchResultItem]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, gt=0)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    answer_text: str
    status: str
    source_chunk_ids: list[UUID]
    model: str
