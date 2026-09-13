from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class RunStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineRunBase(BaseModel):
    trigger_type: str = "MANUAL"
    status: RunStatus = RunStatus.PENDING
    documents_discovered: int = 0
    documents_processed: int = 0
    documents_skipped: int = 0
    chunks_created: int = 0
    embedding_model: str = "text-embedding-3-small"
    total_embedding_tokens: int = 0
    estimated_cost_usd: float = 0.0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class PipelineRunCreate(BaseModel):
    trigger_type: str = "MANUAL"


class PipelineRunResponse(PipelineRunBase):
    id: UUID


class PipelineRunListResponse(BaseModel):
    runs: List[PipelineRunResponse]
    total: int
    skip: int
    limit: int