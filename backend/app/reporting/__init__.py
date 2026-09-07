"""Report view model + HTML and PDF renderers (one data source, two outputs)."""

from .builder import ReportData, build_report_data
from .html import render_html
from .pdf import render_pdf

__all__ = ["ReportData", "build_report_data", "render_html", "render_pdf"]
