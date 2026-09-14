"""Document lifecycle: version manager and SHA-256 conflict resolution."""

from app.ingestion.lifecycle.base import (
    AbstractConflictResolver,
    AbstractVersionManager,
    ConflictAction,
    ConflictError,
    VersionDecision,
)
from app.ingestion.lifecycle.conflict_resolver import SHA256ConflictResolver
from app.ingestion.lifecycle.version_manager import DefaultVersionManager, get_version_manager

__all__ = [
    "AbstractConflictResolver",
    "AbstractVersionManager",
    "ConflictAction",
    "ConflictError",
    "DefaultVersionManager",
    "SHA256ConflictResolver",
    "VersionDecision",
    "get_version_manager",
]
