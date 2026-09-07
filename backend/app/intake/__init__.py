"""Intake: normalize any uploaded appointment list into reviewable rows.

No PHI is sent to an LLM here (Phase 0 gate). CSV/Excel is deterministic; PDF/image
uses AWS Textract. The admin review gate is the correctness backstop.
"""

from .normalizer import get_parser, normalize
from .parsers import ParsedRow

__all__ = ["ParsedRow", "get_parser", "normalize"]
