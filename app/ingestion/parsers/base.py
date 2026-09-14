"""Base parser contract, parsed-document model, and parser factory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.ingestion.chunking.base import estimate_tokens


class ParsedDocument(BaseModel):
    """Structured output of a parser: extracted text plus document metadata."""

    model_config = ConfigDict(extra="forbid")

    text: str = ""
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def token_count(self) -> int:
        return estimate_tokens(self.text)


class ParseError(Exception):
    """Raised when a document cannot be parsed."""


class BaseParser(ABC):
    """Contract for all document format parsers."""

    supported_extensions: ClassVar[set[str]] = set()

    @staticmethod
    def read_bytes(path: Path, max_bytes: int | None = None) -> bytes:
        """Read a file's raw bytes, optionally enforcing a size cap."""
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ParseError(f"Cannot read {path}: {exc}") from exc
        if max_bytes is not None and len(data) > max_bytes:
            raise ParseError(f"File exceeds {max_bytes} byte limit: {path}")
        return data

    @abstractmethod
    def parse(self, path: Path) -> ParsedDocument:
        """Parse the file at ``path`` into a ParsedDocument."""
        raise NotImplementedError

    @classmethod
    def register(cls, extensions: set[str]) -> None:
        """Register this parser for each extension and update the global registry."""
        for ext in extensions:
            ext = ext.lower()
            if ext in _REGISTRY:
                raise ValueError(f"Parser already registered for extension: {ext}")
            _REGISTRY[ext] = cls
        cls.supported_extensions |= {e.lower() for e in extensions}


_REGISTRY: dict[str, type[BaseParser]] = {}


def _ensure_registry() -> None:
    """Lazily import parser modules so their self-registration runs."""
    if ".pdf" in _REGISTRY:
        return
    from app.ingestion.parsers import csv as _csv
    from app.ingestion.parsers import docx as _docx
    from app.ingestion.parsers import html as _html
    from app.ingestion.parsers import pdf as _pdf
    from app.ingestion.parsers import plain_text as _plain

    _ = (_csv, _docx, _html, _pdf, _plain)


def get_parser(filename: str) -> BaseParser:
    """Return the parser registered for a filename's extension.

    Falls back to UTF-8 text parsing for unknown extensions.
    """
    _ensure_registry()
    suffix = Path(filename).suffix.lower()
    parser_cls = _REGISTRY.get(suffix)
    if parser_cls is None:
        from app.ingestion.parsers.plain_text import PlainTextParser

        parser_cls = PlainTextParser
    return parser_cls()


def register_parser(extension: str, parser_cls: type[BaseParser], overwrite: bool = False) -> None:
    """Register a parser for a file extension (e.g. ``".pdf"``)."""
    ext = extension.lower()
    if ext in _REGISTRY and not overwrite:
        raise ValueError(f"Parser already registered for extension: {ext}")
    _REGISTRY[ext] = parser_cls
