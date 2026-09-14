"""Unit tests for the document parsers and parser factory."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest
from app.ingestion.parsers import (
    CSVParser,
    HTMLParser,
    ParsedDocument,
    ParseError,
    PDFParser,
    PlainTextParser,
    get_parser,
)
from app.ingestion.parsers.base import register_parser
from pydantic import ValidationError


class _StubParser(PlainTextParser):
    supported_extensions: ClassVar[set[str]] = {".xyz"}


def _write(tmp_path: Path, name: str, content: str, encoding: str = "utf-8") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding=encoding)
    return path


# ---------------------------------------------------------------------------
# ParsedDocument
# ---------------------------------------------------------------------------


class TestParsedDocument:
    def test_counts_are_computed(self) -> None:
        doc = ParsedDocument(text="hello world")
        assert doc.char_count == 11
        assert doc.token_count == 2  # estimate: ~4 chars per token

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ParsedDocument.model_validate({"text": "x", "surprise": True})

    def test_title_optional(self) -> None:
        assert ParsedDocument(text="x").title is None


# ---------------------------------------------------------------------------
# PlainTextParser
# ---------------------------------------------------------------------------


class TestPlainTextParser:
    def test_parses_txt_and_md(self, tmp_path: Path) -> None:
        txt = _write(tmp_path, "note.txt", "Hello world.")
        md = _write(tmp_path, "guide.md", "# Title\n\nBody text here.")

        doc_txt = PlainTextParser().parse(txt)
        assert doc_txt.text == "Hello world."
        assert doc_txt.title == "note"
        assert doc_txt.metadata == {"extension": ".txt", "encoding": "utf-8"}

        doc_md = PlainTextParser().parse(md)
        assert "# Title" in doc_md.text
        assert doc_md.title == "guide"

    def test_invalid_utf8_raises_parse_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.txt"
        path.write_bytes(b"\xff\xfe\x00binary")
        with pytest.raises(ParseError, match="UTF-8"):
            PlainTextParser().parse(path)

    def test_missing_file_raises_parse_error(self, tmp_path: Path) -> None:
        with pytest.raises(ParseError, match=r"Cannot read|cannot read|decode"):
            PlainTextParser().parse(tmp_path / "nope.txt")


# ---------------------------------------------------------------------------
# HTMLParser
# ---------------------------------------------------------------------------


class TestHTMLParser:
    def _write_html(self, tmp_path: Path) -> Path:
        return _write(
            tmp_path,
            "page.html",
            "<html><head><title>My Page</title><style>p{}</style></head>"
            "<body><h1>Welcome</h1><p>Hello <b>world</b>.</p>"
            "<script>var x = 1;</script><h2>Section A</h2><ul><li>One</li><li>Two</li></ul></body></html>",
        )

    def test_extracts_title_and_headings(self, tmp_path: Path) -> None:
        doc = HTMLParser().parse(self._write_html(tmp_path))
        assert doc.title == "My Page"
        assert doc.metadata["title_tag"] == "My Page"
        assert doc.metadata["headings"] == ["Welcome", "Section A"]

    def test_drops_script_and_style(self, tmp_path: Path) -> None:
        doc = HTMLParser().parse(self._write_html(tmp_path))
        assert "var x" not in doc.text
        assert "p{}" not in doc.text
        assert "Welcome" in doc.text
        assert "One" in doc.text

    def test_layout_keeps_inline_text_together(self, tmp_path: Path) -> None:
        doc = HTMLParser().parse(self._write_html(tmp_path))
        assert "Hello world." in doc.text

    def test_uses_filename_stem_when_no_title(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "plain.html", "<p>no title here</p>")
        doc = HTMLParser().parse(path)
        assert doc.title == "plain"
        assert doc.metadata["title_tag"] is None


# ---------------------------------------------------------------------------
# CSVParser
# ---------------------------------------------------------------------------


class TestCSVParser:
    def test_parses_csv_with_headers(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "data.csv", "name,dept,salary\nada,eng,100\nbob,ops,90\n")
        doc = CSVParser().parse(path)
        assert doc.metadata["delimiter"] == ","
        assert doc.metadata["column_names"] == ["name", "dept", "salary"]
        assert doc.metadata["row_count"] == 2
        assert doc.text.splitlines()[0] == "name, dept, salary"
        assert "ada, eng, 100" in doc.text

    def test_tsv_uses_tab_delimiter(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "data.tsv", "a\tb\n1\t2\n")
        doc = CSVParser().parse(path)
        assert doc.metadata["delimiter"] == "\t"
        assert doc.metadata["column_names"] == ["a", "b"]

    def test_custom_delimiter_overrides(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "data.psv", "a|b\n1|2\n")
        doc = CSVParser(delimiter="|").parse(path)
        assert doc.metadata["delimiter"] == "|"
        assert doc.metadata["column_names"] == ["a", "b"]

    def test_utf8_bom_is_stripped(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "bom.csv", "h1,h2\nx,y\n", encoding="utf-8-sig")
        doc = CSVParser().parse(path)
        assert doc.metadata["column_names"] == ["h1", "h2"]

    def test_empty_file_returns_zero_rows(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "empty.csv", "")
        doc = CSVParser().parse(path)
        assert doc.metadata["row_count"] == 0
        assert doc.text == ""


# ---------------------------------------------------------------------------
# PDF / DOCX (optional dependencies)
# ---------------------------------------------------------------------------


class TestOptionalParsers:
    def test_pdf_raises_install_hint_when_pypdf_missing(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "doc.pdf", "%PDF-1.4")
        with pytest.raises(ParseError, match="pypdf"):
            PDFParser().parse(path)

    def test_docx_raises_install_hint_when_docx_missing(self, tmp_path: Path) -> None:
        from app.ingestion.parsers import DOCXParser

        path = _write(tmp_path, "doc.docx", "PK\x03\x04fake")
        with pytest.raises(ParseError, match=r"python-docx|docx"):
            DOCXParser().parse(path)


# ---------------------------------------------------------------------------
# Parser factory / registry
# ---------------------------------------------------------------------------


class TestGetParser:
    def test_registry_routes_extensions(self) -> None:
        assert isinstance(get_parser("a.txt"), PlainTextParser)
        assert isinstance(get_parser("a.md"), PlainTextParser)
        assert isinstance(get_parser("a.html"), HTMLParser)
        assert isinstance(get_parser("a.htm"), HTMLParser)
        assert isinstance(get_parser("a.csv"), CSVParser)
        assert isinstance(get_parser("a.tsv"), CSVParser)
        assert isinstance(get_parser("a.pdf"), PDFParser)

    def test_unknown_extension_falls_back_to_plain_text(self) -> None:
        assert isinstance(get_parser("notes.rtf"), PlainTextParser)
        assert isinstance(get_parser("archive"), PlainTextParser)

    def test_extension_lookup_is_case_insensitive(self) -> None:
        assert isinstance(get_parser("A.HTML"), HTMLParser)

    def test_register_parser_rejects_duplicate(self) -> None:
        with pytest.raises(ValueError, match="already registered"):
            register_parser(".txt", _StubParser)

    def test_register_parser_overwrite_allowed(self) -> None:
        register_parser(".novel", _StubParser, overwrite=True)
        try:
            assert isinstance(get_parser("x.novel"), _StubParser)
        finally:
            from app.ingestion.parsers.base import _REGISTRY

            _REGISTRY.pop(".novel", None)
