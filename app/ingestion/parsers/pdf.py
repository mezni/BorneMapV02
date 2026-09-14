"""PDF text parser (requires the optional ``pypdf`` dependency)."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from app.ingestion.parsers.base import BaseParser, ParsedDocument, ParseError

try:  # pragma: no cover - exercised only when pypdf is installed
    from pypdf import PdfReader  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - pypdf is optional
    PdfReader = None


class PDFParser(BaseParser):
    """Extracts text from PDF documents (``.pdf``).

    Requires ``pypdf``; install with ``uv add pypdf``.
    """

    supported_extensions: ClassVar[set[str]] = {".pdf"}

    def parse(self, path: Path) -> ParsedDocument:
        if PdfReader is None:
            raise ParseError("pypdf is not installed; install it with: uv add pypdf")
        raw = self.read_bytes(path)
        try:
            reader = PdfReader(raw)
        except Exception as exc:
            raise ParseError(f"Cannot read PDF {path}: {exc}") from exc

        pages_text: list[str] = []
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:  # some encrypted/malformed pages raise
                raise ParseError(f"Cannot extract text from PDF {path}: {exc}") from exc
            pages_text.append(page_text.strip())

        return ParsedDocument(
            text="\n\n".join(p for p in pages_text if p),
            title=path.stem,
            metadata={"page_count": len(reader.pages)},
        )


PDFParser.register(PDFParser.supported_extensions)
