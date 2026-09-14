from uuid import UUID, uuid4
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class RunStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineRun:
    """Domain entity tracking an execution instance of the document ingestion pipeline.

    Captures process metrics, versioning lineage, and FinOps embedding token costs.
    """

    def __init__(
        self,
        id: Optional[UUID] = None,
        trigger_type: str = "MANUAL",
        status: RunStatus = RunStatus.PENDING,
        documents_discovered: int = 0,
        documents_processed: int = 0,
        documents_skipped: int = 0,
        chunks_created: int = 0,
        embedding_model: str = "text-embedding-3-small",
        total_embedding_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        started_at: datetime = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ):
        self.id = id or uuid4()
        self.trigger_type = trigger_type
        self.status = status
        self.documents_discovered = documents_discovered
        self.documents_processed = documents_processed
        self.documents_skipped = documents_skipped
        self.chunks_created = chunks_created
        self.embedding_model = embedding_model
        self.total_embedding_tokens = total_embedding_tokens
        self.estimated_cost_usd = estimated_cost_usd
        self.started_at = started_at or datetime.now(timezone.utc)
        self.completed_at = completed_at
        self.error_message = error_message
        self.metadata = metadata or {}

    def complete(self, cost_usd: float = 0.0) -> None:
        """Marks the ingestion run as successfully completed."""
        self.status = RunStatus.COMPLETED
        self.estimated_cost_usd = cost_usd
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, error_msg: str) -> None:
        """Marks the ingestion run as failed with error details."""
        self.status = RunStatus.FAILED
        self.error_message = error_msg
        self.completed_at = datetime.now(timezone.utc)