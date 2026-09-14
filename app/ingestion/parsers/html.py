"""HTML parser using the standard-library HTMLParser."""

from __future__ import annotations

from html.parser import HTMLParser as StdlibHTMLParser
from pathlib import Path
from typing import ClassVar

from app.ingestion.parsers.base import BaseParser, ParsedDocument, ParseError

_SKIP_TAGS = {"script", "style", "noscript", "template"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_BLOCK_TAGS = _HEADING_TAGS | {"p", "li", "div", "section", "article", "blockquote", "pre", "tr", "br"}
_NO_LEADING_SPACE = {".", ",", ";", ":", "!", "?", ")", "]", "}"}


class _HTMLTextExtractor(StdlibHTMLParser):
    """Collects readable text, headings, and title, dropping script/style content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.buffer = ""
        self.title: str | None = None
        self.headings: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._in_heading: str | None = None

    def _append_break(self) -> None:
        if self.buffer and not self.buffer.endswith("\n"):
            self.buffer += "\n"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS and self._skip_depth == 0:
            self._skip_depth = 1
        elif self._skip_depth:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in _HEADING_TAGS and self._in_heading is None:
            self._in_heading = tag
            self._append_break()
        elif tag in _BLOCK_TAGS:
            self._append_break()
        if tag == "br":
            self._append_break()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if self._in_heading == tag:
            self._in_heading = None
            self._append_break()

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if self._in_title:
            if stripped:
                self.title = stripped
            return
        if self._skip_depth or not stripped:
            return
        if self._in_heading:
            self.headings.append(stripped)
        if self.buffer and not self.buffer.endswith(("\n", " ")):
            if stripped[:1] not in _NO_LEADING_SPACE:
                self.buffer += " "
        self.buffer += stripped


class HTMLParser(BaseParser):
    """Parses HTML documents (``.html``, ``.htm``) into readable text."""

    supported_extensions: ClassVar[set[str]] = {".html", ".htm"}

    def parse(self, path: Path) -> ParsedDocument:
        raw = self.read_bytes(path)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ParseError(f"Cannot decode {path} as UTF-8: {exc}") from exc

        extractor = _HTMLTextExtractor()
        try:
            extractor.feed(text)
            extractor.close()
        except Exception as exc:  # html.parser handles some malformed inputs via overrides
            raise ParseError(f"Cannot parse HTML {path}: {exc}") from exc

        body = extractor.buffer.strip()
        return ParsedDocument(
            text=body,
            title=extractor.title or path.stem,
            metadata={
                "extension": path.suffix,
                "headings": extractor.headings,
                "title_tag": extractor.title,
            },
        )


HTMLParser.register(HTMLParser.supported_extensions)
