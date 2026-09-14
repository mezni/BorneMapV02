"""Plain-text and Markdown parser."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from app.ingestion.parsers.base import BaseParser, ParsedDocument, ParseError


class PlainTextParser(BaseParser):
    """Parses UTF-8 text files (``.txt``, ``.md``, ``.markdown``)."""

    supported_extensions: ClassVar[set[str]] = {".txt", ".md", ".markdown"}

    def parse(self, path: Path) -> ParsedDocument:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ParseError(f"Cannot decode {path} as UTF-8 text: {exc}") from exc
        return ParsedDocument(
            text=text,
            title=path.stem,
            metadata={"extension": path.suffix, "encoding": "utf-8"},
        )


PlainTextParser.register(PlainTextParser.supported_extensions)
