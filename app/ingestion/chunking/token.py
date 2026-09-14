"""Token-budget chunker that splits strictly on estimated token count."""

from __future__ import annotations

from uuid import UUID

from app.core.config import TokenChunking
from app.domain.models.chunk import Chunk, ChunkType
from app.ingestion.chunking.base import BaseChunker, estimate_tokens, split_sentences


class TokenChunker(BaseChunker):
    """Splits text into chunks of at most ``chunk_size`` estimated tokens.

    Uses the estimated-token budget (approx. 4 chars/token) and enforces
    ``chunk_overlap`` tokens of trailing context between consecutive chunks,
    aligned on sentence boundaries where possible.
    """

    chunk_type = ChunkType.PARENT

    def __init__(self, config: TokenChunking | None = None, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size if config is None else config.chunk_size
        self.chunk_overlap = chunk_overlap if config is None else config.chunk_overlap
        self._overlap_chars = int(self.chunk_overlap * 4.0)

    def _chunk(self, text: str, document_id: UUID, document_version_id: UUID) -> list[Chunk]:
        sentences = split_sentences(text)
        chunks: list[Chunk] = []
        buffer: list[str] = []

        def flush() -> None:
            nonlocal buffer
            if not buffer:
                return
            body = " ".join(buffer)
            chunks.append(
                Chunk(
                    document_id=document_id,
                    document_version_id=document_version_id,
                    chunk_index=len(chunks),
                    chunk_type=self.chunk_type,
                    content=body,
                    token_count=estimate_tokens(body),
                    char_count=len(body),
                )
            )
            # Keep only the overlap tail for the next chunk.
            kept: list[str] = []
            kept_len = 0
            for sent in reversed(buffer):
                if kept_len + len(sent) + 1 <= self._overlap_chars:
                    kept.insert(0, sent)
                    kept_len += len(sent) + 1
                else:
                    break
            buffer = kept if kept else []

        for sent in sentences:
            if estimate_tokens(sent) > self.chunk_size:
                flush()
                # Oversized single sentence: hard-split on word groups.
                for word_group in sent.split():
                    if estimate_tokens(word_group) > self.chunk_size and word_group:
                        chunks.append(
                            Chunk(
                                document_id=document_id,
                                document_version_id=document_version_id,
                                chunk_index=len(chunks),
                                chunk_type=self.chunk_type,
                                content=word_group,
                                token_count=estimate_tokens(word_group),
                                char_count=len(word_group),
                            )
                        )
                    else:
                        buffer.append(word_group)
                        if estimate_tokens(" ".join(buffer)) > self.chunk_size:
                            buffer.pop()
                            flush()
                            buffer.append(word_group)
                continue
            prospective = [*buffer, sent]
            if estimate_tokens(" ".join(prospective)) > self.chunk_size:
                flush()
            buffer.append(sent)
        flush()
        return chunks
