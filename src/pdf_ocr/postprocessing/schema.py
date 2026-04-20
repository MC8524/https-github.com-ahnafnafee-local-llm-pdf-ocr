"""Dataclasses returned by the postprocessing layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional


@dataclass
class ExtractedField:
    name: str
    value: str
    parsed: Any = None
    valid: Optional[bool] = None
    source_line: str = ""


@dataclass
class DocumentResult:
    text: str
    pages_text: dict[int, list[str]]
    fields: dict[str, list[ExtractedField]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    output_pdf: str = ""

    def first(self, name: str) -> Optional[ExtractedField]:
        """Convenience: first field with this name, or None."""
        values = self.fields.get(name) or []
        return values[0] if values else None

    def first_decimal(self, name: str) -> Optional[Decimal]:
        f = self.first(name)
        if f is None:
            return None
        parsed = f.parsed
        return parsed if isinstance(parsed, Decimal) else None
