"""Document version manager: decides first-time indexing, updates, and deduplication."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentVersionStatus,
)
from app.ingestion.lifecycle.base import (
    AbstractConflictResolver,
    AbstractVersionManager,
    ConflictAction,
    ConflictError,
    VersionDecision,
)
from app.ingestion.lifecycle.conflict_resolver import SHA256ConflictResolver


class DefaultVersionManager(AbstractVersionManager):
    """Versioning policy over an incoming ``Document`` versus the indexed corpus.

    The manager is repository-agnostic; it receives ``Document`` instances and
    answers purely in terms of domain objects. ``decide()`` returns a
    ``VersionDecision`` whose ``document`` is what the caller should persist:

    - ``NEW``: persist as-is (first index).
    - ``UPDATE``: persist the returned existing document, which now carries the
      new version (previous active version marked ``SUPERSEDED``, source metadata
      refreshed, ``previous_content_hash`` recorded).
    - ``SKIP``: do **not** persist — ``documents.checksum_sha256`` is unique, so
      a duplicate row cannot be stored; count it as skipped instead.
    - ``CONFLICT``: ``ConflictError`` is raised; no side effects are applied.

    Lookups are injected as callables so the manager stays DB-agnostic; when only
    a path lookup is provided, cross-path content deduplication does not trigger.
    """

    def __init__(
        self,
        conflict_resolver: AbstractConflictResolver | None = None,
        lookup_by_path: Callable[[str], Document | None] | None = None,
        lookup_by_checksum: Callable[[str], Document | None] | None = None,
        max_versions: int | None = None,
    ) -> None:
        self._resolver = conflict_resolver or SHA256ConflictResolver()
        self._lookup_by_path = lookup_by_path
        self._lookup_by_checksum = lookup_by_checksum
        self._max_versions = max_versions

    def decide(self, incoming: Document) -> VersionDecision:
        checksum = self._incoming_checksum(incoming)
        path = self._incoming_path(incoming)

        existing = self._find_existing(path, checksum)
        if existing is None:
            incoming.status = DocumentStatus.PENDING
            return VersionDecision(
                action=ConflictAction.NEW,
                reason=f"No prior record for source path '{path}'; indexing for the first time",
                document=incoming,
                created_version=incoming.current_version,
            )

        action, reason = self._resolver.resolve(checksum, path, existing)

        if action is ConflictAction.SKIP:
            incoming.status = DocumentStatus.SKIPPED
            return VersionDecision(action=ConflictAction.SKIP, reason=reason, document=incoming)

        if action is ConflictAction.UPDATE:
            return self._apply_update(incoming, existing, reason)

        raise ConflictError(reason)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_existing(self, path: str, checksum: str) -> Document | None:
        if self._lookup_by_path is not None and path:
            existing = self._lookup_by_path(path)
            if existing is not None:
                return existing
        if self._lookup_by_checksum is not None:
            return self._lookup_by_checksum(checksum)
        return None

    def _apply_update(self, incoming: Document, existing: Document, reason: str) -> VersionDecision:
        new_version = incoming.current_version
        if new_version is None:
            raise ConflictError("Incoming document has no current version to assign; cannot create a new version")

        previous_checksum = existing.source_metadata.checksum_sha256 if existing.source_metadata else None

        new_version.document_id = existing.id
        new_version.version_number = len(existing.versions) + 1

        if existing.current_version is not None:
            existing.current_version.status = DocumentVersionStatus.SUPERSEDED

        existing.versions.append(new_version)
        existing.current_version = new_version
        existing.status = DocumentStatus.PROCESSING
        existing.updated_at = datetime.now(UTC)

        if previous_checksum:
            existing.metadata["previous_content_hash"] = previous_checksum

        self._refresh_source_metadata(existing, incoming)
        self._archive_excess_versions(existing)

        return VersionDecision(
            action=ConflictAction.UPDATE,
            reason=reason,
            document=existing,
            created_version=new_version,
        )

    @staticmethod
    def _refresh_source_metadata(existing: Document, incoming: Document) -> None:
        """Copy fresh file stats from the incoming scan onto the existing document."""
        incoming_meta = incoming.source_metadata
        existing_meta = existing.source_metadata
        if incoming_meta is None or existing_meta is None:
            return
        existing_meta.checksum_sha256 = incoming_meta.checksum_sha256
        existing_meta.file_size_bytes = incoming_meta.file_size_bytes
        existing_meta.last_modified = incoming_meta.last_modified
        existing_meta.mime_type = incoming_meta.mime_type
        existing_meta.file_extension = incoming_meta.file_extension
        existing_meta.file_name = incoming_meta.file_name

    def _archive_excess_versions(self, document: Document) -> None:
        """Archive the oldest versions beyond ``max_versions`` (newest kept)."""
        if self._max_versions is None:
            return
        excess = document.versions[: max(0, len(document.versions) - self._max_versions)]
        count = 0
        for stale in excess:
            if stale.status is not DocumentVersionStatus.ARCHIVED:
                stale.status = DocumentVersionStatus.ARCHIVED
                count += 1
        if count:
            document.metadata["archived_versions"] = document.metadata.get("archived_versions", 0) + count

    @staticmethod
    def _incoming_checksum(document: Document) -> str:
        checksum = document.source_metadata.checksum_sha256 if document.source_metadata else ""
        if not checksum:
            raise ValueError("Incoming document is missing a SHA-256 checksum; cannot resolve its lifecycle")
        return checksum

    @staticmethod
    def _incoming_path(document: Document) -> str:
        return document.source_metadata.source_path if document.source_metadata else ""


def get_version_manager(
    conflict_resolver: AbstractConflictResolver | None = None,
    lookup_by_path: Callable[[str], Document | None] | None = None,
    lookup_by_checksum: Callable[[str], Document | None] | None = None,
    max_versions: int | None = None,
) -> AbstractVersionManager:
    """Instantiate the default version manager (convenience factory)."""
    return DefaultVersionManager(
        conflict_resolver=conflict_resolver,
        lookup_by_path=lookup_by_path,
        lookup_by_checksum=lookup_by_checksum,
        max_versions=max_versions,
    )
