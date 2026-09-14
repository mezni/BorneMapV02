"""Unit tests for the chunkers, chunk helpers, and the chunker factory."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.core.config import (
    ChunkingConfig,
    ParentChildChunking,
    RecursiveChunking,
    SemanticChunking,
)
from app.domain.models.chunk import Chunk, ChunkType
from app.ingestion.chunking.base import (
    BaseChunker,
    estimate_tokens,
    get_chunker,
    split_paragraphs,
    split_sentences,
)
from app.ingestion.chunking.parent_child import ParentChildChunker
from app.ingestion.chunking.recursive import RecursiveChunker
from app.ingestion.chunking.semantic import SemanticChunker
from app.ingestion.chunking.token import TokenChunker

DOC_ID = uuid4()
VERSION_ID = uuid4()


def _ids() -> tuple[object, object]:
    return DOC_ID, VERSION_ID


@pytest.fixture
def ids() -> tuple[object, object]:
    return DOC_ID, VERSION_ID


def _first_chunk(chunks: list[Chunk]) -> Chunk:
    assert chunks
    return chunks[0]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class TestChunkHelpers:
    def test_estimate_tokens_scales_with_length(self) -> None:
        assert estimate_tokens("") == 1
        assert estimate_tokens("abcd") == 1
        assert estimate_tokens("abcd" * 100) == 100

    def test_split_sentences(self) -> None:
        assert split_sentences("One. Two! Three?") == ["One.", "Two!", "Three?"]
        assert split_sentences("") == []

    def test_split_paragraphs(self) -> None:
        assert split_paragraphs("Para one.\n\nPara two.") == ["Para one.", "Para two."]
        assert split_paragraphs("\n\n\nonly\n\n\n") == ["only"]


# ---------------------------------------------------------------------------
# RecursiveChunker
# ---------------------------------------------------------------------------


class TestRecursiveChunker:
    def _chunks(self, text: str, chunk_size: int = 200, overlap: int = 20) -> list[Chunk]:
        chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=overlap)
        return chunker.chunk_text(text, DOC_ID, VERSION_ID)

    def test_empty_text_yields_no_chunks(self) -> None:
        assert self._chunks("") == []
        assert self._chunks("   \n ") == []

    def test_chunks_are_persistent_ready(self, ids: tuple[object, object]) -> None:
        text = "Session established.\n\n" + ("word group " * 60)
        chunks = self._chunks(text)
        first = _first_chunk(chunks)
        assert first.document_id == DOC_ID
        assert first.document_version_id == VERSION_ID
        assert first.chunk_type is ChunkType.PARENT
        assert first.chunk_index == 0
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_contents_are_reassembled_in_order(self) -> None:
        text = "The quick brown fox jumps.\n\nThe lazy dog sleeps."
        chunks = self._chunks(text, chunk_size=300, overlap=0)
        assert len(chunks) == 1
        assert "The quick brown fox jumps." in chunks[0].content
        assert "lazy dog sleeps" in chunks[0].content

    def test_long_text_produces_multiple_bounded_chunks(self) -> None:
        text = "sentence of words with context here. " * 200
        chunks = self._chunks(text, chunk_size=100, overlap=20)
        assert len(chunks) >= 2
        for c in chunks:
            assert c.token_count <= 100
            assert c.char_count == len(c.content)

    def test_overlap_tail_carried_between_chunks(self) -> None:
        text = "alpha beta gamma delta epsilon zeta eta theta. " * 60
        chunks = self._chunks(text, chunk_size=80, overlap=30)
        assert len(chunks) >= 2
        head = " ".join(chunks[1].content.split()[:4])
        assert head in chunks[0].content, "overlap content should reappear in the next chunk"

    def test_chunk_spans_tracked_in_metadata(self) -> None:
        chunks = self._chunks("abc " * 120, chunk_size=80, overlap=20)
        first = _first_chunk(chunks)
        assert isinstance(first.metadata.get("start_char"), int)
        assert isinstance(first.metadata.get("end_char"), int)
        assert first.metadata["end_char"] > first.metadata["start_char"]

    def test_config_object_overrides_defaults(self) -> None:
        chunker = RecursiveChunker(RecursiveChunking(chunk_size=500, chunk_overlap=10))
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 10


# ---------------------------------------------------------------------------
# TokenChunker
# ---------------------------------------------------------------------------


class TestTokenChunker:
    def test_respects_token_budget(self) -> None:
        text = "word ".join(["token"] * 400)
        chunker = TokenChunker(chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk_text(text, DOC_ID, VERSION_ID)
        assert len(chunks) >= 2
        for c in chunks:
            assert c.token_count <= 100

    def test_oversized_sentence_hard_split(self) -> None:
        text = "x " * 300
        chunker = TokenChunker(chunk_size=50, chunk_overlap=10)
        chunks = chunker.chunk_text(text, DOC_ID, VERSION_ID)
        assert len(chunks) > 1

    def test_short_text_single_chunk(self) -> None:
        chunker = TokenChunker(chunk_size=512, chunk_overlap=64)
        chunks = chunker.chunk_text("Just a short sentence here.", DOC_ID, VERSION_ID)
        assert len(chunks) == 1
        assert "short sentence" in chunks[0].content


# ---------------------------------------------------------------------------
# SemanticChunker
# ---------------------------------------------------------------------------


class TestSemanticChunker:
    def test_fallback_packs_without_embedder(self) -> None:
        text = " ".join(["A sentence here."] * 50)
        chunker = SemanticChunker(max_tokens=100)
        chunks = chunker.chunk_text(text, DOC_ID, VERSION_ID)
        assert len(chunks) >= 2
        for c in chunks:
            assert c.token_count <= chunker.max_tokens + 1

    def test_embedder_boundaries_split_by_similarity(self) -> None:
        # Embeddings: sentence1 is like sentence2, both very different from the rest.
        def embed(_list: list[str]) -> list[list[float]]:
            return [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]

        text = "Topic A one. Topic A two. Topic B one. Topic B two."
        chunker = SemanticChunker(embed_func=embed, similarity_threshold=0.9, max_tokens=1000)
        chunks = chunker.chunk_text(text, DOC_ID, VERSION_ID)
        assert len(chunks) >= 2
        assert "Topic A one." in chunks[0].content
        assert "Topic A two." in chunks[0].content
        assert "Topic B one." in chunks[1].content

    def test_config_and_threshold_are_mutually_exclusive(self) -> None:
        with pytest.raises(ValueError, match="either config or similarity_threshold"):
            SemanticChunker(config=SemanticChunking(similarity_threshold=0.3), similarity_threshold=0.4)

    def test_config_threshold_default_applied(self) -> None:
        chunker = SemanticChunker(SemanticChunking(similarity_threshold=0.6))
        assert chunker.threshold == 0.6

    def test_cosine_similarity(self) -> None:
        from app.ingestion.chunking.semantic import _cosine_similarity

        assert _cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
        assert _cosine_similarity([], []) == 0.0


# ---------------------------------------------------------------------------
# ParentChildChunker
# ---------------------------------------------------------------------------


class TestParentChildChunker:
    def test_returns_parents_then_children(self) -> None:
        text = "policy sentence. " * 200  # long enough to yield multiple parents
        chunker = ParentChildChunker()  # default sizes
        chunks = chunker.chunk_text(text, DOC_ID, VERSION_ID)
        assert len(chunks) > 2
        types = [c.chunk_type for c in chunks]
        assert types.count(ChunkType.PARENT) > 0
        assert types.count(ChunkType.CHILD) > 0
        # parents appear before children
        assert types.index(ChunkType.CHILD) > types.index(ChunkType.PARENT)

    def test_children_link_to_containing_parent(self) -> None:
        text = ("intro paragraph. " * 20) + ("detail paragraph. " * 20)
        chunker = ParentChildChunker()
        chunks = chunker.chunk_text(text, DOC_ID, VERSION_ID)
        parents = [c for c in chunks if c.chunk_type is ChunkType.PARENT]
        children = [c for c in chunks if c.chunk_type is ChunkType.CHILD]
        assert parents and children
        parent_ids = {p.id for p in parents}
        for child in children:
            assert child.parent_chunk_id in parent_ids
            containing = next(p for p in parents if p.id == child.parent_chunk_id)
            start = child.metadata.get("start_char", 0)
            assert containing.metadata["start_char"] <= start < containing.metadata["end_char"]

    def test_config_scales_chunk_sizes(self) -> None:
        chunker = ParentChildChunker(
            ParentChildChunking(parent_chunk_size=400, child_chunk_size=200, child_chunk_overlap=20)
        )
        assert chunker._parent_chunker.chunk_size == 400
        assert chunker._child_chunker.chunk_size == 200

    def test_empty_text_returns_empty(self) -> None:
        assert ParentChildChunker().chunk_text("", DOC_ID, VERSION_ID) == []


# ---------------------------------------------------------------------------
# Chunk model
# ---------------------------------------------------------------------------


class TestChunkModel:
    def test_defaults_and_to_dict(self) -> None:
        chunk = Chunk(document_id=DOC_ID, document_version_id=VERSION_ID, content="hi")
        assert chunk.chunk_type is ChunkType.PARENT
        assert chunk.parent_chunk_id is None
        data = chunk.to_dict()
        assert data["content"] == "hi"
        assert data["document_version_id"] == str(VERSION_ID)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestGetChunker:
    def _config(self, strategy: str) -> ChunkingConfig:
        return ChunkingConfig.model_validate({"strategy": strategy})

    def test_strategy_mapping(self) -> None:
        assert isinstance(get_chunker(self._config("recursive")), RecursiveChunker)
        assert isinstance(get_chunker(self._config("token")), TokenChunker)
        assert isinstance(get_chunker(self._config("semantic")), SemanticChunker)
        assert isinstance(get_chunker(self._config("parent_child")), ParentChildChunker)

    def test_unknown_strategy_rejected_at_config(self) -> None:
        with pytest.raises(ValueError):
            ChunkingConfig.model_validate({"strategy": "blocky"})

    def test_returned_chunkers_are_base_chunkers(self) -> None:
        assert isinstance(get_chunker(self._config("recursive")), BaseChunker)
