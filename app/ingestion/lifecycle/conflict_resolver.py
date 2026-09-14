"""SHA-256 based conflict resolution for document ingestion."""

from __future__ import annotations

from app.domain.models.document import Document
from app.ingestion.lifecycle.base import AbstractConflictResolver, ConflictAction


class SHA256ConflictResolver(AbstractConflictResolver):
    """Resolves ingestion conflicts by comparing source paths and content digests.

    Policy:
    - same path, same SHA-256  -> ``SKIP`` (unchanged since last index)
    - same path, new SHA-256   -> ``UPDATE`` (content changed, new version needed)
    - different path, same SHA-256 -> ``SKIP`` when ``deduplicate_content`` is True
      (the document is already in the corpus), otherwise ``CONFLICT``
    - different path, different SHA-256 -> ``CONFLICT`` (cannot attribute automatically)
    """

    def __init__(self, deduplicate_content: bool = True) -> None:
        self._deduplicate_content = deduplicate_content

    def resolve(
        self,
        incoming_checksum: str,
        incoming_path: str,
        existing: Document,
    ) -> tuple[ConflictAction, str]:
        if not incoming_checksum:
            return ConflictAction.CONFLICT, "Incoming document is missing a SHA-256 checksum"

        existing_checksum = existing.source_metadata.checksum_sha256 if existing.source_metadata else ""
        existing_path = existing.source_metadata.source_path if existing.source_metadata else ""

        same_path = bool(incoming_path) and incoming_path == existing_path
        same_content = bool(incoming_checksum) and incoming_checksum == existing_checksum

        if same_path and same_content:
            return (
                ConflictAction.SKIP,
                f"Content unchanged since last index (same SHA-256 '{incoming_checksum[:12]}')",
            )

        if same_path and not same_content:
            return (
                ConflictAction.UPDATE,
                "Content changed since last index (SHA-256 differs); creating a new version",
            )

        if same_content:
            if self._deduplicate_content:
                return (
                    ConflictAction.SKIP,
                    f"Identical SHA-256 already indexed at '{existing_path}'; skipping duplicate content",
                )
            return (
                ConflictAction.CONFLICT,
                f"Identical SHA-256 '{incoming_checksum[:12]}' at different path '{existing_path}'",
            )

        return (
            ConflictAction.CONFLICT,
            f"Different provenance: paths differ and content differs ('{existing_path}' vs '{incoming_path}')",
        )
