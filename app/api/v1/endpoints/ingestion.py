from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.db.repositories.pipeline_run_repository import SQLAlchemyPipelineRunRepository
from app.domain.models.pipeline_runs import PipelineRun, RunStatus
from app.ingestion.pipeline import IngestionPipeline
from app.api.schemas.ingestion import (
    PipelineRunCreate,
    PipelineRunResponse,
    PipelineRunListResponse,
    RunStatus as SchemaRunStatus,
)

router = APIRouter(tags=["ingestion"])


def get_pipeline_run_repo(db: Session = Depends(get_db)) -> SQLAlchemyPipelineRunRepository:
    return SQLAlchemyPipelineRunRepository(db)


def map_domain_to_schema(run: PipelineRun) -> PipelineRunResponse:
    return PipelineRunResponse(
        id=run.id,
        trigger_type=run.trigger_type,
        status=SchemaRunStatus(run.status.value),
        documents_discovered=run.documents_discovered,
        documents_processed=run.documents_processed,
        documents_skipped=run.documents_skipped,
        chunks_created=run.chunks_created,
        embedding_model=run.embedding_model,
        total_embedding_tokens=run.total_embedding_tokens,
        estimated_cost_usd=run.estimated_cost_usd,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
        metadata=run.metadata,
    )


@router.post("/run", response_model=PipelineRunResponse, status_code=202)
async def run_ingestion_pipeline(
    background_tasks: BackgroundTasks,
    payload: PipelineRunCreate,
    repo: SQLAlchemyPipelineRunRepository = Depends(get_pipeline_run_repo),
):
    """Trigger an ingestion pipeline run."""
    pipeline_run = PipelineRun(trigger_type=payload.trigger_type.upper())
    repo.add(pipeline_run)
    
    def run_pipeline():
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            repo_local = SQLAlchemyPipelineRunRepository(db)
            run = repo_local.get(pipeline_run.id)
            if run:
                pipeline = IngestionPipeline()
                result = pipeline.run(run)
                run.complete()
                repo_local.update(run)
        finally:
            db.close()
    
    background_tasks.add_task(run_pipeline)
    
    return map_domain_to_schema(pipeline_run)


@router.get("/runs", response_model=PipelineRunListResponse)
async def list_pipeline_runs(
    skip: int = 0,
    limit: int = 100,
    repo: SQLAlchemyPipelineRunRepository = Depends(get_pipeline_run_repo),
):
    """Get pipeline runs history."""
    return PipelineRunListResponse(runs=[], total=0, skip=skip, limit=limit)


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    run_id: UUID,
    repo: SQLAlchemyPipelineRunRepository = Depends(get_pipeline_run_repo),
):
    """Get a specific pipeline run by ID."""
    run = repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return map_domain_to_schema(run)