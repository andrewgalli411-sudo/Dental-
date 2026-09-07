"""Pick a parser by file type and normalize an upload into ParsedRows."""

from __future__ import annotations

from app.config import get_settings

from .parsers import CsvExcelParser, DocumentParser, ParsedRow, TextractParser

_CSV_EXCEL_EXT = (".csv", ".tsv", ".xlsx", ".xlsm")
_TEXTRACT_EXT = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff")


def get_parser(filename: str) -> DocumentParser:
    lower = filename.lower()
    if lower.endswith(_CSV_EXCEL_EXT):
        return CsvExcelParser()
    if lower.endswith(_TEXTRACT_EXT):
        return TextractParser(region=get_settings().aws_region)
    # Unknown extension: try CSV/Excel first — many exports lack a clean suffix.
    return CsvExcelParser()


def normalize(data: bytes, filename: str) -> list[ParsedRow]:
    return get_parser(filename).parse(data, filename)
