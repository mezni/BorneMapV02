"""CSV/TSV parser using the standard-library csv module."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import ClassVar

from app.ingestion.parsers.base import BaseParser, ParsedDocument, ParseError


class CSVParser(BaseParser):
    """Parses delimiter-separated tabular files (``.csv``, ``.tsv``).

    Rows are flattened into readable text with headers preserved; metadata
    records delimiter, column names, and row count.
    """

    supported_extensions: ClassVar[set[str]] = {".csv", ".tsv"}

    def __init__(self, delimiter: str | None = None) -> None:
        self._delimiter = delimiter

    def _resolve_delimiter(self, path: Path) -> str:
        if self._delimiter is not None:
            return self._delimiter
        return "\t" if path.suffix.lower() == ".tsv" else ","

    def parse(self, path: Path) -> ParsedDocument:
        raw = self.read_bytes(path)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ParseError(f"Cannot decode {path} as UTF-8: {exc}") from exc

        delimiter = self._resolve_delimiter(path)
        reader = csv.reader(text.splitlines(), delimiter=delimiter)
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]

        if not rows:
            return ParsedDocument(text="", title=path.stem, metadata={"delimiter": delimiter, "row_count": 0})

        headers = rows[0]
        expanded = [", ".join(headers)]
        for row in rows[1:]:
            padded = row + [""] * (len(headers) - len(row))
            expanded.append(", ".join(padded[: len(headers)]))

        return ParsedDocument(
            text="\n".join(expanded),
            title=path.stem,
            metadata={
                "delimiter": delimiter,
                "column_names": headers,
                "row_count": len(rows) - 1,
            },
        )


CSVParser.register(CSVParser.supported_extensions)
