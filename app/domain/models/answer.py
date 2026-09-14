"""Core domain entity for Answer."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AnswerStatus(StrEnum):
    GENERATED = "generated"
    FAILED = "failed"
    NO_CONTEXT = "no_context"


class Answer(BaseModel):
    """A grounded answer produced by the generation pipeline."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    query: str = ""
    answer_text: str = ""
    status: AnswerStatus = AnswerStatus.GENERATED
    source_chunk_ids: list[UUID] = Field(default_factory=list)
    model: str = ""
    input_token_count: int = 0
    output_token_count: int = 0
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
