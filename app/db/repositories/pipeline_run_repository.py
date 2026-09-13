from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.db.models.pipeline_runs import PipelineRunORM
from app.domain.models.pipeline_runs import PipelineRun, RunStatus
from app.domain.interfaces.pipeline_run_repository import AbstractPipelineRunRepository

class SQLAlchemyPipelineRunRepository(AbstractPipelineRunRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_orm_model(self, pipeline_run: PipelineRun) -> PipelineRunORM:
        return PipelineRunORM(
            id=pipeline_run.id,
            trigger_type=pipeline_run.trigger_type,
            status=pipeline_run.status.value,
            documents_discovered=pipeline_run.documents_discovered,
            documents_processed=pipeline_run.documents_processed,
            documents_skipped=pipeline_run.documents_skipped,
            chunks_created=pipeline_run.chunks_created,
            embedding_model=pipeline_run.embedding_model,
            total_embedding_tokens=pipeline_run.total_embedding_tokens,
            estimated_cost_usd=pipeline_run.estimated_cost_usd,
            started_at=pipeline_run.started_at,
            completed_at=pipeline_run.completed_at,
            error_message=pipeline_run.error_message,
            metadata_=pipeline_run.metadata,
        )

    def _to_domain_model(self, pipeline_run_orm: PipelineRunORM) -> PipelineRun:
        return PipelineRun(
            id=pipeline_run_orm.id,
            trigger_type=pipeline_run_orm.trigger_type,
            status=RunStatus(pipeline_run_orm.status),
            documents_discovered=pipeline_run_orm.documents_discovered,
            documents_processed=pipeline_run_orm.documents_processed,
            documents_skipped=pipeline_run_orm.documents_skipped,
            chunks_created=pipeline_run_orm.chunks_created,
            embedding_model=pipeline_run_orm.embedding_model,
            total_embedding_tokens=pipeline_run_orm.total_embedding_tokens,
            estimated_cost_usd=pipeline_run_orm.estimated_cost_usd,
            started_at=pipeline_run_orm.started_at,
            completed_at=pipeline_run_orm.completed_at,
            error_message=pipeline_run_orm.error_message,
            metadata=pipeline_run_orm.metadata_,
        )

    def add(self, pipeline_run: PipelineRun) -> None:
        pipeline_run_orm = self._to_orm_model(pipeline_run)
        self.session.add(pipeline_run_orm)

    def get(self, run_id: UUID) -> Optional[PipelineRun]:
        pipeline_run_orm = self.session.query(PipelineRunORM).filter_by(id=run_id).first()
        if pipeline_run_orm:
            return self._to_domain_model(pipeline_run_orm)
        return None

    def list(self, skip: int = 0, limit: int = 100) -> List[PipelineRun]:
        pipeline_runs_orm = self.session.query(PipelineRunORM).order_by(PipelineRunORM.started_at.desc()).offset(skip).limit(limit).all()
        return [self._to_domain_model(orm) for orm in pipeline_runs_orm]

    def update(self, pipeline_run: PipelineRun) -> None:
        pipeline_run_orm = self.session.query(PipelineRunORM).filter_by(id=pipeline_run.id).first()
        if pipeline_run_orm:
            pipeline_run_orm.trigger_type = pipeline_run.trigger_type
            pipeline_run_orm.status = pipeline_run.status.value
            pipeline_run_orm.documents_discovered = pipeline_run.documents_discovered
            pipeline_run_orm.documents_processed = pipeline_run.documents_processed
            pipeline_run_orm.documents_skipped = pipeline_run.documents_skipped
            pipeline_run_orm.chunks_created = pipeline_run.chunks_created
            pipeline_run_orm.embedding_model = pipeline_run.embedding_model
            pipeline_run_orm.total_embedding_tokens = pipeline_run.total_embedding_tokens
            pipeline_run_orm.estimated_cost_usd = pipeline_run.estimated_cost_usd
            pipeline_run_orm.started_at = pipeline_run.started_at
            pipeline_run_orm.completed_at = pipeline_run.completed_at
            pipeline_run_orm.error_message = pipeline_run.error_message
            pipeline_run_orm.metadata_ = pipeline_run.metadata
            self.session.flush() # Flush to ensure changes are detected by the session

    def delete(self, run_id: UUID) -> None:
        pipeline_run_orm = self.session.query(PipelineRunORM).filter_by(id=run_id).first()
        if pipeline_run_orm:
            self.session.delete(pipeline_run_orm)
