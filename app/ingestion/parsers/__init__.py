"""Document parsers: Plain Text, HTML, CSV, PDF, and DOCX."""

from app.ingestion.parsers.base import (
    BaseParser,
    ParsedDocument,
    ParseError,
    get_parser,
    register_parser,
)
from app.ingestion.parsers.csv import CSVParser
from app.ingestion.parsers.docx import DOCXParser
from app.ingestion.parsers.html import HTMLParser
from app.ingestion.parsers.pdf import PDFParser
from app.ingestion.parsers.plain_text import PlainTextParser

__all__ = [
    "BaseParser",
    "CSVParser",
    "DOCXParser",
    "HTMLParser",
    "PDFParser",
    "ParseError",
    "ParsedDocument",
    "PlainTextParser",
    "get_parser",
    "register_parser",
]
