"""Recursive character-aware chunker (paragraph -> sentence -> word)."""

from __future__ import annotations

from uuid import UUID

from app.core.config import RecursiveChunking
from app.domain.models.chunk import Chunk, ChunkType
from app.ingestion.chunking.base import (
    BaseChunker,
    _whitespace_tail,
    estimate_tokens,
    split_paragraphs,
    split_sentences,
)


def _split_words(text: str) -> list[str]:
    """Split text into whitespace-delimited word groups."""
    return [w for w in text.split() if w]


class RecursiveChunker(BaseChunker):
    """Splits text using a separator hierarchy: paragraphs, then sentences, then words.

    Chunks are greedily packed to stay within ``chunk_size`` estimated tokens,
    carrying ``chunk_overlap`` tokens of the previous chunk tail for context.
    """

    chunk_type = ChunkType.PARENT

    def __init__(self, config: RecursiveChunking | None = None, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size if config is None else config.chunk_size
        self.chunk_overlap = chunk_overlap if config is None else config.chunk_overlap
        self._overlap_chars = int(self.chunk_overlap * 4.0)

    def _segments(self, text: str, level: int = 0) -> list[tuple[str, int]]:
        """Returns (segment_text, char_offset) pieces with span tracking.

        ``level`` 0 = paragraph cascade, 1 = sentence cascade, 2 = word cascade.
        """
        if level == 0:
            pieces = split_paragraphs(text)
        elif level == 1:
            pieces = split_sentences(text)
        else:
            return self._word_segments(text)

        segments: list[tuple[str, int]] = []
        offset = 0
        for piece in pieces:
            if not piece:
                continue
            # If this piece is itself too large, cascade into finer granularity.
            if estimate_tokens(piece) > self.chunk_size:
                if level < 2:
                    nested = self._segments(piece, level + 1)
                    if nested:
                        segments.extend(nested)
                        continue
                segments.append((piece, offset))
            else:
                segments.append((piece, offset))
            offset += len(piece) + 1
        return segments

    def _word_segments(self, text: str) -> list[tuple[str, int]]:
        words = _split_words(text)
        out: list[tuple[str, int]] = []
        offset = 0
        for word in words:
            out.append((word, offset))
            offset += len(word) + 1
        return out

    def _chunk(self, text: str, document_id: UUID, document_version_id: UUID) -> list[Chunk]:
        segments = self._segments(text)
        chunks: list[Chunk] = []
        current: list[tuple[str, int]] = []
        current_start = 0

        def flush() -> None:
            nonlocal current, current_start
            if not current:
                return
            body = " ".join(seg for seg, _ in current)
            end = current[-1][1] + len(current[-1][0])
            metadata = {"start_char": current_start, "end_char": end}
            chunks.append(
                Chunk(
                    document_id=document_id,
                    document_version_id=document_version_id,
                    chunk_index=len(chunks),
                    chunk_type=self.chunk_type,
                    content=body,
                    token_count=estimate_tokens(body),
                    char_count=len(body),
                    metadata=metadata,
                )
            )
            # Carry overlap tail into next chunk.
            overlap_tail = _whitespace_tail(body, self._overlap_chars)
            suffix = [(overlap_tail, max(0, end - len(overlap_tail)))] if overlap_tail else []
            current = suffix
            if suffix:
                current_start = suffix[0][1]
            else:
                current_start = end

        for seg, offset in segments:
            if not current:
                current_start = offset
                current = [(seg, offset)]
                continue
            prospective = [*current, (seg, offset)]
            if estimate_tokens(" ".join(s for s, _ in prospective)) <= self.chunk_size:
                current = prospective
            else:
                flush()
                if not current:
                    current = [(seg, offset)]
                    current_start = offset
        flush()
        return chunks
