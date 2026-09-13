from sqlalchemy import Column, String, Integer, DateTime, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.session import Base
from app.domain.models.pipeline_runs import RunStatus
import uuid
import datetime

class PipelineRunORM(Base):
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger_type = Column(String, nullable=False, default="MANUAL")
    status = Column(String, nullable=False, default=RunStatus.PENDING.value)
    
    # Discovery & Ingestion Statistics
    documents_discovered = Column(Integer, nullable=False, default=0)
    documents_processed = Column(Integer, nullable=False, default=0)
    documents_skipped = Column(Integer, nullable=False, default=0)
    chunks_created = Column(Integer, nullable=False, default=0)
    
    # FinOps Token Accounting
    embedding_model = Column(String, nullable=False, default="text-embedding-3-small")
    total_embedding_tokens = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)
    
    # Execution Timestamps & Audit
    started_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, default={}) # Use metadata_ to avoid conflict with sqlalchemy.sql.schema.MetaData

    def __repr__(self):
        return f"<PipelineRunORM(id={self.id}, status='{self.status}')>"
