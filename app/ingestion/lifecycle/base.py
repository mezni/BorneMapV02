"""Contracts for document lifecycle management: versioning and SHA-256 conflict resolution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.domain.models.document import Document, DocumentVersion


class ConflictAction(StrEnum):
    """Outcome of comparing an incoming document against the indexed corpus."""

    NEW = "new"
    """No prior record: the document should be indexed for the first time."""
    UPDATE = "update"
    """Same source path, different content: create a new version and supersede the old one."""
    SKIP = "skip"
    """Identical content already indexed: deduplicate, do not persist."""
    CONFLICT = "conflict"
    """Ambiguous provenance: requires manual or policy-driven resolution."""


class VersionDecision(BaseModel):
    """What the version manager decided for an incoming document."""

    model_config = ConfigDict(extra="forbid")

    action: ConflictAction
    reason: str
    document: Document
    created_version: DocumentVersion | None = None


class ConflictError(Exception):
    """Raised when an incoming document cannot be resolved automatically."""


class AbstractConflictResolver(ABC):
    """Compares an incoming file (path + SHA-256) against an indexed document."""

    @abstractmethod
    def resolve(
        self,
        incoming_checksum: str,
        incoming_path: str,
        existing: Document,
    ) -> tuple[ConflictAction, str]:
        """Decide an action and human-readable reason for an incoming file."""
        raise NotImplementedError


class AbstractVersionManager(ABC):
    """Decides how an incoming document should be versioned against the corpus."""

    @abstractmethod
    def decide(self, incoming: Document) -> VersionDecision:
        """Produce a versioning decision for an incoming document."""
        raise NotImplementedError
