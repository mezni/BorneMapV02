"""Unit tests for the ingestion lifecycle (version manager + SHA-256 conflict resolver)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from app.domain.metadata.source import SourceMetadata, SourceType
from app.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentVersion,
    DocumentVersionStatus,
)
from app.ingestion.lifecycle import (
    ConflictAction,
    ConflictError,
    DefaultVersionManager,
    SHA256ConflictResolver,
    VersionDecision,
)

CHECKSUM_A = "a" * 64
CHECKSUM_B = "b" * 64


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _source_metadata(checksum: str, path: str, size: int = 100) -> SourceMetadata:
    return SourceMetadata(
        source_type=SourceType.FILESYSTEM,
        source_path=path,
        file_name=Path(path).name,
        file_extension=Path(path).suffix,
        file_size_bytes=size,
        mime_type="text/plain",
        checksum_sha256=checksum,
        last_modified=datetime(2026, 1, 1),
    )


def _incoming(checksum: str, path: str = "docs/a.txt") -> Document:
    source = _source_metadata(checksum, path)
    version = DocumentVersion(content_hash=checksum, source_metadata=source)
    document = Document(title="a", source_metadata=source, status=DocumentStatus.PENDING)
    document.add_version(version)
    return document


def _existing(
    checksum: str,
    path: str = "docs/a.txt",
    version_number: int = 1,
    versions: int = 1,
) -> Document:
    source = _source_metadata(checksum, path, size=50)
    document = Document(title="a", source_metadata=source, status=DocumentStatus.COMPLETED)
    for i in range(1, versions + 1):
        assert i == 1, "helper builds only one version; use the manager to grow history"
        version = DocumentVersion(
            content_hash=checksum,
            source_metadata=source,
            version_number=version_number,
            status=DocumentVersionStatus.ACTIVE,
            processed_at=datetime(2026, 1, 2),
        )
        document.versions = [version]
        document.current_version = version
    return document


# ---------------------------------------------------------------------------
# SHA256ConflictResolver
# ---------------------------------------------------------------------------


class TestSHA256ConflictResolver:
    def test_same_path_same_checksum_skips(self) -> None:
        action, _ = SHA256ConflictResolver().resolve(CHECKSUM_A, "docs/a.txt", _existing(CHECKSUM_A))
        assert action is ConflictAction.SKIP

    def test_same_path_different_checksum_updates(self) -> None:
        action, _ = SHA256ConflictResolver().resolve(CHECKSUM_B, "docs/a.txt", _existing(CHECKSUM_A))
        assert action is ConflictAction.UPDATE

    def test_different_path_same_checksum_dedup_skips_by_default(self) -> None:
        action, _ = SHA256ConflictResolver().resolve(CHECKSUM_A, "docs/alias.txt", _existing(CHECKSUM_A, "docs/a.txt"))
        assert action is ConflictAction.SKIP

    def test_different_path_same_checksum_conflicts_when_not_dedup(self) -> None:
        resolver = SHA256ConflictResolver(deduplicate_content=False)
        action, _ = resolver.resolve(CHECKSUM_A, "docs/alias.txt", _existing(CHECKSUM_A, "docs/a.txt"))
        assert action is ConflictAction.CONFLICT

    def test_different_provenance_conflicts(self) -> None:
        action, _ = SHA256ConflictResolver().resolve(CHECKSUM_B, "docs/other.txt", _existing(CHECKSUM_A, "docs/a.txt"))
        assert action is ConflictAction.CONFLICT

    def test_empty_incoming_checksum_is_neither_skip_nor_update(self) -> None:
        action, _ = SHA256ConflictResolver().resolve("", "docs/a.txt", _existing(CHECKSUM_A))
        assert action is ConflictAction.CONFLICT


# ---------------------------------------------------------------------------
# DefaultVersionManager
# ---------------------------------------------------------------------------


class TestDefaultVersionManager:
    def _manager(self, **kwargs: object) -> DefaultVersionManager:
        return DefaultVersionManager(**kwargs)  # type: ignore[arg-type]

    def test_new_document_gets_new_decision(self) -> None:
        manager = DefaultVersionManager()
        incoming = _incoming(CHECKSUM_A)
        decision = manager.decide(incoming)
        assert decision.action is ConflictAction.NEW
        assert decision.created_version is incoming.current_version
        assert incoming.status is DocumentStatus.PENDING

    def test_unchanged_document_is_skipped(self) -> None:
        store: dict[str, Document] = {"docs/a.txt": _existing(CHECKSUM_A)}
        manager = DefaultVersionManager(lookup_by_path=store.get)
        decision = manager.decide(_incoming(CHECKSUM_A))
        assert decision.action is ConflictAction.SKIP
        assert decision.created_version is None
        assert decision.document.status is DocumentStatus.SKIPPED

    def test_changed_document_creates_new_version(self) -> None:
        existing = _existing(CHECKSUM_A)
        store: dict[str, Document] = {"docs/a.txt": existing}
        manager = DefaultVersionManager(lookup_by_path=store.get)
        decision = manager.decide(_incoming(CHECKSUM_B))
        assert decision.action is ConflictAction.UPDATE
        assert decision.document is existing
        assert decision.created_version is not None
        assert decision.created_version.version_number == 2
        assert existing.current_version is decision.created_version
        assert existing.versions[0].status is DocumentVersionStatus.SUPERSEDED
        assert existing.source_metadata is not None
        assert existing.source_metadata.checksum_sha256 == CHECKSUM_B
        assert existing.source_metadata.file_size_bytes == 100
        assert existing.metadata["previous_content_hash"] == CHECKSUM_A
        assert existing.status is DocumentStatus.PROCESSING

    def test_duplicate_content_at_other_path_is_skipped_via_checksum_lookup(self) -> None:
        existing = _existing(CHECKSUM_A, "docs/a.txt")
        store: dict[str, Document] = {CHECKSUM_A: existing}
        manager = DefaultVersionManager(lookup_by_checksum=store.get)
        decision = manager.decide(_incoming(CHECKSUM_A, "docs/copy.txt"))
        assert decision.action is ConflictAction.SKIP
        assert decision.document.status is DocumentStatus.SKIPPED

    def test_unmatched_path_is_treated_as_new(self) -> None:
        store: dict[str, Document] = {"docs/a.txt": _existing(CHECKSUM_A)}
        manager = DefaultVersionManager(lookup_by_path=store.get)
        decision = manager.decide(_incoming(CHECKSUM_B, "docs/new.txt"))
        assert decision.action is ConflictAction.NEW
        assert decision.document.status is DocumentStatus.PENDING

    def test_non_dedup_duplicate_raises_conflict(self) -> None:
        resolver = SHA256ConflictResolver(deduplicate_content=False)
        store: dict[str, Document] = {CHECKSUM_A: _existing(CHECKSUM_A, "docs/a.txt")}
        manager = DefaultVersionManager(
            conflict_resolver=resolver,
            lookup_by_checksum=store.get,
        )
        with pytest.raises(ConflictError, match=r"[Dd]ifferent path|Different provenance"):
            manager.decide(_incoming(CHECKSUM_A, "docs/copy.txt"))

    def test_missing_checksum_raises_value_error(self) -> None:
        manager = DefaultVersionManager()
        incoming = _incoming(CHECKSUM_A)
        assert incoming.source_metadata is not None
        incoming.source_metadata.checksum_sha256 = ""
        with pytest.raises(ValueError, match="SHA-256 checksum"):
            manager.decide(incoming)

    def test_max_versions_archives_oldest(self) -> None:
        existing = _existing(CHECKSUM_A)
        store: dict[str, Document] = {"docs/a.txt": existing}
        manager = DefaultVersionManager(lookup_by_path=store.get, max_versions=2)
        manager.decide(_incoming(CHECKSUM_B))  # v2
        decision = manager.decide(_incoming(CHECKSUM_A.replace("a", "c")))  # v3
        assert decision.action is ConflictAction.UPDATE
        assert len(existing.versions) == 3
        assert existing.versions[0].status is DocumentVersionStatus.ARCHIVED
        assert existing.versions[1].status is DocumentVersionStatus.SUPERSEDED
        assert existing.versions[2].status is not DocumentVersionStatus.ARCHIVED
        assert existing.metadata["archived_versions"] == 1

    def test_decision_is_a_pydantic_model(self) -> None:
        manager = DefaultVersionManager()
        decision = manager.decide(_incoming(CHECKSUM_A))
        assert isinstance(decision, VersionDecision)
        assert decision.model_dump()["action"] == ConflictAction.NEW.value

    def test_factory_returns_default_manager(self) -> None:
        from app.ingestion.lifecycle import get_version_manager

        manager = get_version_manager()
        assert isinstance(manager, DefaultVersionManager)
