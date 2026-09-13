from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from app.domain.models.pipeline_runs import PipelineRun


class AbstractPipelineRunRepository(ABC):
    @abstractmethod
    def add(self, pipeline_run: PipelineRun) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, run_id: UUID) -> Optional[PipelineRun]:
        raise NotImplementedError

    @abstractmethod
    def update(self, pipeline_run: PipelineRun) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, run_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100) -> List[PipelineRun]:
        raise NotImplementedError
