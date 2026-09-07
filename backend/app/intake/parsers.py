"""Document parsers: turn an uploaded file into normalized rows.

Two implementations behind one protocol:
- CsvExcelParser  — deterministic, no external calls, no LLM. Handles the common
  case (a PMS day-sheet exported to CSV/XLSX) with fuzzy header mapping.
- TextractParser  — PDF/scanned images via AWS Textract (BAA-covered). Activated
  at Phase 0; imports boto3 lazily.

Neither sends PHI to an LLM. Imperfect parses are expected — the admin review gate
(Phase 3) is the correctness backstop, which is why every row carries a confidence
and an `issues` list.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol, runtime_checkable

# Canonical field -> accepted header aliases (compared lowercased/stripped).
_HEADER_ALIASES: dict[str, set[str]] = {
    "patient_name": {
        "patient", "patient name", "name", "pt name", "pt", "patient_name",
        "full name", "member name",
    },
    "dob": {
        "dob", "d.o.b.", "date of birth", "birthdate", "birth date", "born",
    },
    "payer_name": {
        "payer", "payer name", "insurance", "insurance company", "carrier",
        "plan", "insurance carrier", "ins", "coverage",
    },
    "subscriber_id": {
        "subscriber id", "subscriber", "member id", "member #", "member number",
        "insurance id", "id", "policy id", "policy #", "policy number", "memberid",
    },
    "subscriber_name": {"subscriber name", "policy holder", "guarantor", "insured"},
    "subscriber_dob": {"subscriber dob", "insured dob", "policy holder dob"},
    "payer_id": {"payer id", "payer_id", "electronic payer id", "edi payer id"},
    "group_number": {"group", "group number", "group #", "grp", "grp #"},
    "appt_time": {
        "time", "appt", "appt time", "appointment", "appointment time", "appt.",
        "sched time", "scheduled",
    },
}

_REQUIRED = ("patient_name", "dob", "payer_name")

_DATE_FORMATS = (
    "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y",
    "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y %H:%M",
)


@dataclass(slots=True)
class ParsedRow:
    patient_name: str | None = None
    dob: date | None = None
    payer_name: str | None = None
    subscriber_id: str | None = None
    subscriber_name: str | None = None
    subscriber_dob: date | None = None
    payer_id: str | None = None
    group_number: str | None = None
    appt_time: datetime | None = None
    confidence: float = 0.0
    issues: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return bool(self.issues) or self.confidence < 1.0


@runtime_checkable
class DocumentParser(Protocol):
    def parse(self, data: bytes, filename: str) -> list[ParsedRow]:
        ...


def _try_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _map_headers(headers: list[str]) -> dict[int, str]:
    """Map column index -> canonical field via alias table."""
    mapping: dict[int, str] = {}
    for idx, raw in enumerate(headers):
        key = (raw or "").strip().lower()
        for field_name, aliases in _HEADER_ALIASES.items():
            if key in aliases:
                mapping[idx] = field_name
                break
    return mapping


def _row_from(values: list[str], col_map: dict[int, str]) -> ParsedRow:
    row = ParsedRow()
    for idx, field_name in col_map.items():
        if idx >= len(values):
            continue
        raw = (values[idx] or "").strip()
        if not raw:
            continue
        if field_name == "dob":
            row.dob = _try_date(raw)
            if row.dob is None:
                row.issues.append(f"unparseable dob: {raw!r}")
        elif field_name == "subscriber_dob":
            row.subscriber_dob = _try_date(raw)
        elif field_name == "appt_time":
            row.appt_time = _parse_appt_time(raw)
        else:
            setattr(row, field_name, raw)

    _score(row)
    return row


def _parse_appt_time(raw: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _score(row: ParsedRow) -> None:
    present = 0
    for f in _REQUIRED:
        if getattr(row, f):
            present += 1
        else:
            row.issues.append(f"missing required field: {f}")
    row.confidence = present / len(_REQUIRED)


class CsvExcelParser:
    """Deterministic parser for CSV and XLSX exports."""

    def parse(self, data: bytes, filename: str) -> list[ParsedRow]:
        lower = filename.lower()
        if lower.endswith((".xlsx", ".xlsm")):
            table = self._read_xlsx(data)
        else:
            table = self._read_csv(data)
        if not table:
            return []
        headers, *rows = table
        col_map = _map_headers(headers)
        if not col_map:
            # Header row not recognized; surface a single flagged row so the
            # batch lands in review rather than silently empty.
            r = ParsedRow(issues=["unrecognized columns — needs manual mapping"])
            return [r]
        return [_row_from(values, col_map) for values in rows if any(v.strip() for v in values)]

    @staticmethod
    def _read_csv(data: bytes) -> list[list[str]]:
        text = data.decode("utf-8-sig", errors="replace")
        return [list(row) for row in csv.reader(io.StringIO(text))]

    @staticmethod
    def _read_xlsx(data: bytes) -> list[list[str]]:
        from openpyxl import load_workbook  # lazy import

        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        table: list[list[str]] = []
        for row in ws.iter_rows(values_only=True):
            table.append(["" if c is None else str(c) for c in row])
        wb.close()
        return table


class TextractParser:
    """PDF / scanned-image parser via AWS Textract (Phase 0). boto3 lazy-imported."""

    def __init__(self, region: str) -> None:
        self._region = region

    def parse(self, data: bytes, filename: str) -> list[ParsedRow]:  # pragma: no cover
        import boto3

        client = boto3.client("textract", region_name=self._region)
        resp = client.analyze_document(
            Document={"Bytes": data}, FeatureTypes=["TABLES"]
        )
        table = _textract_tables_to_grid(resp)
        if not table:
            return [ParsedRow(issues=["textract found no table — needs manual entry"])]
        headers, *rows = table
        col_map = _map_headers(headers)
        if not col_map:
            return [ParsedRow(issues=["unrecognized columns — needs manual mapping"])]
        return [_row_from(v, col_map) for v in rows if any(x.strip() for x in v)]


def _textract_tables_to_grid(resp: dict) -> list[list[str]]:  # pragma: no cover
    """Flatten Textract TABLE/CELL blocks into a row-major grid."""
    blocks = {b["Id"]: b for b in resp.get("Blocks", [])}
    grids: list[list[list[str]]] = []
    for block in resp.get("Blocks", []):
        if block.get("BlockType") != "TABLE":
            continue
        cells: dict[tuple[int, int], str] = {}
        max_r = max_c = 0
        for rel in block.get("Relationships", []):
            if rel.get("Type") != "CHILD":
                continue
            for cid in rel["Ids"]:
                cell = blocks.get(cid, {})
                if cell.get("BlockType") != "CELL":
                    continue
                r, c = cell["RowIndex"], cell["ColumnIndex"]
                max_r, max_c = max(max_r, r), max(max_c, c)
                cells[(r, c)] = _cell_text(cell, blocks)
        grid = [
            [cells.get((r, c), "") for c in range(1, max_c + 1)]
            for r in range(1, max_r + 1)
        ]
        grids.append(grid)
    return grids[0] if grids else []


def _cell_text(cell: dict, blocks: dict) -> str:  # pragma: no cover
    words: list[str] = []
    for rel in cell.get("Relationships", []):
        if rel.get("Type") != "CHILD":
            continue
        for wid in rel["Ids"]:
            w = blocks.get(wid, {})
            if w.get("BlockType") in ("WORD", "SELECTION_ELEMENT"):
                words.append(w.get("Text", ""))
    return " ".join(words).strip()
