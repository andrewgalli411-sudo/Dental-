"""Render ReportData to the HTML web view (Jinja2)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .builder import ReportData

_TEMPLATES = Path(__file__).parent / "templates"


def _money(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return f"${value:,.2f}"


_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html"]),
)
_env.filters["money"] = _money


def render_html(data: ReportData) -> str:
    return _env.get_template("report.html").render(data=data)
