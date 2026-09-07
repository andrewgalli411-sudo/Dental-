from __future__ import annotations

import csv
import io
from datetime import date

from app.intake import normalize
from app.intake.parsers import CsvExcelParser


def _csv(rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8")


def test_fuzzy_headers_map_to_canonical_fields() -> None:
    data = _csv(
        [
            ["Patient Name", "DOB", "Insurance", "Member ID", "Group #", "Time"],
            ["Jane Doe", "01/15/1990", "Delta Dental", "ABC123", "GRP9", "09:00"],
        ]
    )
    rows = CsvExcelParser().parse(data, "sheet.csv")
    assert len(rows) == 1
    r = rows[0]
    assert r.patient_name == "Jane Doe"
    assert r.dob == date(1990, 1, 15)
    assert r.payer_name == "Delta Dental"
    assert r.subscriber_id == "ABC123"
    assert r.group_number == "GRP9"
    assert r.confidence == 1.0
    assert r.needs_review is False


def test_missing_required_field_flags_review() -> None:
    data = _csv(
        [
            ["Patient", "DOB", "Member ID"],  # no payer column
            ["John Smith", "1985-06-30", "XYZ"],
        ]
    )
    rows = CsvExcelParser().parse(data, "sheet.csv")
    r = rows[0]
    assert r.payer_name is None
    assert r.needs_review is True
    assert any("payer_name" in i for i in r.issues)
    assert r.confidence < 1.0


def test_unparseable_dob_is_flagged() -> None:
    data = _csv([["Name", "DOB", "Carrier"], ["A B", "not-a-date", "Cigna"]])
    r = CsvExcelParser().parse(data, "s.csv")[0]
    assert r.dob is None
    assert any("dob" in i for i in r.issues)


def test_unrecognized_columns_yield_single_flagged_row() -> None:
    data = _csv([["colA", "colB"], ["1", "2"]])
    rows = CsvExcelParser().parse(data, "s.csv")
    assert len(rows) == 1
    assert rows[0].needs_review is True
    assert any("unrecognized" in i for i in rows[0].issues)


def test_multiple_date_formats() -> None:
    for raw, expected in [
        ("12/31/2000", date(2000, 12, 31)),
        ("2000-12-31", date(2000, 12, 31)),
        ("Dec 31, 2000", date(2000, 12, 31)),
    ]:
        data = _csv([["Name", "DOB", "Payer"], ["X", raw, "P"]])
        assert normalize(data, "s.csv")[0].dob == expected


def test_blank_rows_skipped() -> None:
    data = _csv(
        [
            ["Patient", "DOB", "Payer"],
            ["Jane", "01/01/1990", "Aetna"],
            ["", "", ""],
        ]
    )
    assert len(CsvExcelParser().parse(data, "s.csv")) == 1
