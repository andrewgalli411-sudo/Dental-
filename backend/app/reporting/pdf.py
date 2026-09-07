"""Render ReportData to a printable PDF (fpdf2 — pure Python, no native deps)."""

from __future__ import annotations

from decimal import Decimal

from fpdf import FPDF

from .builder import ReportData

# (header, width mm, align) — widths sum to ~277 (A4 landscape usable width).
_COLUMNS = [
    ("Time", 20, "L"),
    ("Patient", 48, "L"),
    ("Payer / Plan", 52, "L"),
    ("Status", 22, "L"),
    ("Annual", 26, "R"),
    ("Remaining", 26, "R"),
    ("Deductible", 33, "R"),
    ("Notes", 50, "L"),
]


def _money(value: Decimal | None) -> str:
    return "-" if value is None else f"${value:,.2f}"


def _safe(text: str) -> str:
    """Built-in fpdf fonts are latin-1 only; real patient names contain other
    characters. Replace anything unencodable rather than crash the report.
    (A bundled Unicode TTF would render them properly — a later polish item.)"""
    return text.encode("latin-1", "replace").decode("latin-1")


def _clip(text: str, width_mm: float) -> str:
    # ~2mm per char at 8pt; keep cells single-line.
    text = _safe(text)
    limit = max(4, int(width_mm / 1.8))
    return text if len(text) <= limit else text[: limit - 3] + "..."


def render_pdf(data: ReportData) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 8, "Insurance Eligibility Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(
        0, 6, _safe(f"{data.practice_name}  |  {data.generated_at}"),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.cell(
        0, 6,
        f"{len(data.rows)} patients   {data.verified_count} verified   "
        f"{data.unverified_count} need attention",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)

    # Header row.
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(26, 32, 39)  # --ink; neutral header, no decorative color
    for title, width, align in _COLUMNS:
        pdf.cell(width, 7, title, border=0, align=align, fill=True)
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    fill = False
    for r in data.rows:
        deductible = (
            f"{_money(r.deductible_met)}/{_money(r.deductible_total)}"
            if r.deductible_total is not None
            else "-"
        )
        payer = r.payer or "-"
        if r.plan:
            payer = f"{payer} ({r.plan})"
        note = r.note or ""
        values = [
            r.appt_time or "-",
            r.patient_name,
            payer,
            r.status.replace("_", " ").title(),
            _money(r.annual_max),
            _money(r.remaining_benefit),
            deductible,
            note,
        ]
        pdf.set_fill_color(248, 250, 252)
        for (_, width, align), value in zip(_COLUMNS, values, strict=True):
            pdf.cell(width, 6, _clip(str(value), width), border="B", align=align, fill=fill)
        pdf.ln(6)
        fill = not fill

    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(
        0, 4,
        "Verified by verifi-dental. Confirm coverage at time of service; benefits "
        "quoted are not a guarantee of payment. Contains PHI.",
    )

    out = pdf.output()
    return bytes(out)
