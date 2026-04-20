"""
Contextual field extraction for Brazilian fiscal documents.

Output: dict[name -> list[ExtractedField]] + list of warnings.
Each ExtractedField records the raw match, its parsed form (Decimal, date),
validity (CPF/CNPJ checksum), and the source line for audit.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable, Optional

from src.pdf_ocr.postprocessing.schema import ExtractedField
from src.pdf_ocr.postprocessing.validators import (
    brl_to_decimal,
    cnpj_valid,
    cpf_valid,
    date_parse,
)


CPF_RE = re.compile(r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b")
CNPJ_RE = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b")
BRL_RE = re.compile(r"R\$\s*([\d\.]+,\d{2})")
DATE_NUM_RE = re.compile(r"\b(\d{2}[/\-.]\d{2}[/\-.]\d{2,4})\b")
COMPETENCIA_RE = re.compile(
    r"(?:compet[êe]ncia[:\s-]*)?(\b\d{2}/\d{4}\b)", re.IGNORECASE
)
AGENCIA_RE = re.compile(r"ag[êe]ncia[:\s]*(\d{3,6}(?:-?\d)?)", re.IGNORECASE)
CONTA_RE = re.compile(r"(?:conta(?:\s+corrente)?|c/c|cc)[:\s]*(\d{3,12}-?\d)", re.IGNORECASE)
AUTH_RE = re.compile(
    r"(?:autentica[çc][ãa]o|c[oó]digo\s+de\s+autentica[çc][ãa]o|hash)[:\s]*([A-Z0-9\.\-]{8,64})",
    re.IGNORECASE,
)
PIX_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
PIX_EMAIL_RE = re.compile(r"\b[\w\.\-]+@[\w\.\-]+\.[a-z]{2,}\b", re.IGNORECASE)
PIX_PHONE_RE = re.compile(r"\+?55\s*\(?\d{2}\)?\s*9?\d{4}-?\d{4}\b")
DCTF_RECIBO_RE = re.compile(
    r"(?:n[uú]mero\s+do\s+recibo|recibo\s+n[oº°]?)[:\s]*([A-Z0-9\.\-]{8,})",
    re.IGNORECASE,
)


CONTRACHEQUE_LABELS: dict[str, list[str]] = {
    "salario_bruto": [
        r"(?:sal[aá]rio\s+bruto|total\s+(?:de\s+)?(?:vencimentos|proventos)|total\s+bruto|vencimentos)",
    ],
    "inss": [r"(?:inss|i\.n\.s\.s\.?|previd[êe]ncia\s+oficial)"],
    "irrf": [r"(?:irrf|i\.r\.r\.f\.?|imposto\s+de\s+renda(?:\s+retido)?)"],
    "fgts": [r"(?:fgts|f\.g\.t\.s\.?)"],
    "liquido": [
        r"(?:l[ií]quido\s+a\s+receber|valor\s+l[ií]quido|total\s+l[ií]quido|l[ií]quido)"
    ],
}


def _source_line(text: str, span: tuple[int, int]) -> str:
    start, end = span
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()


def _scan_simple(
    text: str,
    pattern: re.Pattern[str],
    name: str,
    *,
    fields: dict[str, list[ExtractedField]],
    validator: Optional[Callable[[str], bool]] = None,
    parser: Optional[Callable[[str], object]] = None,
) -> None:
    seen: set[str] = set()
    bucket = fields.setdefault(name, [])
    for m in pattern.finditer(text):
        raw = m.group(1) if m.groups() else m.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        valid = validator(raw) if validator else None
        parsed = parser(raw) if parser else None
        bucket.append(
            ExtractedField(
                name=name,
                value=raw,
                parsed=parsed,
                valid=valid,
                source_line=_source_line(text, m.span()),
            )
        )


def _scan_labeled_brl(
    text: str,
    label_patterns: list[str],
    name: str,
    fields: dict[str, list[ExtractedField]],
) -> None:
    """
    Scan each line of `text` for a label near a BRL value on the same line.
    Takes the LAST occurrence — totals usually live at the bottom.
    """
    bucket: list[ExtractedField] = []
    for line in text.split("\n"):
        for lp in label_patterns:
            if not re.search(lp, line, re.IGNORECASE):
                continue
            brl_match = BRL_RE.search(line)
            value: str
            parsed: Optional[Decimal]
            if brl_match:
                value = brl_match.group(1)
                parsed = brl_to_decimal(value)
            else:
                # Try a bare number in comma-decimal format.
                m = re.search(r"(\d{1,3}(?:\.\d{3})*|\d+),\d{2}", line)
                if not m:
                    continue
                value = m.group(0)
                parsed = brl_to_decimal(value)
            bucket.append(
                ExtractedField(
                    name=name,
                    value=value,
                    parsed=parsed,
                    valid=None,
                    source_line=line.strip(),
                )
            )
            break  # one match per line is enough
    if bucket:
        # Prefer the LAST occurrence for totals-at-the-bottom.
        fields[name] = bucket


class ContextualExtractor:
    """Regex + validator extractor. Stateless — call `extract` per document."""

    def extract(
        self, text: str
    ) -> tuple[dict[str, list[ExtractedField]], list[str]]:
        fields: dict[str, list[ExtractedField]] = {}
        warnings: list[str] = []

        _scan_simple(text, CPF_RE, "cpf", fields=fields, validator=cpf_valid)
        _scan_simple(text, CNPJ_RE, "cnpj", fields=fields, validator=cnpj_valid)
        _scan_simple(text, BRL_RE, "brl", fields=fields, parser=brl_to_decimal)
        _scan_simple(
            text, DATE_NUM_RE, "date", fields=fields,
            parser=lambda s: date_parse(s),
        )
        _scan_simple(text, COMPETENCIA_RE, "competencia", fields=fields)
        _scan_simple(text, AGENCIA_RE, "agencia", fields=fields)
        _scan_simple(text, CONTA_RE, "conta", fields=fields)
        _scan_simple(text, AUTH_RE, "auth_code", fields=fields)
        _scan_simple(text, PIX_UUID_RE, "pix_uuid", fields=fields)
        _scan_simple(text, PIX_EMAIL_RE, "pix_email", fields=fields)
        _scan_simple(text, PIX_PHONE_RE, "pix_phone", fields=fields)
        _scan_simple(text, DCTF_RECIBO_RE, "dctf_recibo", fields=fields)

        for key, patterns in CONTRACHEQUE_LABELS.items():
            _scan_labeled_brl(text, patterns, key, fields)

        self._consistency_checks(fields, warnings)
        return fields, warnings

    def _consistency_checks(
        self,
        fields: dict[str, list[ExtractedField]],
        warnings: list[str],
    ) -> None:
        for cpf in fields.get("cpf", []):
            if cpf.valid is False:
                warnings.append(f"CPF {cpf.value} falhou no checksum mod-11")
        for cnpj in fields.get("cnpj", []):
            if cnpj.valid is False:
                warnings.append(f"CNPJ {cnpj.value} falhou no checksum mod-11")

        bruto = _first_decimal(fields.get("salario_bruto"))
        inss = _first_decimal(fields.get("inss"))
        irrf = _first_decimal(fields.get("irrf"))
        liquido = _first_decimal(fields.get("liquido"))
        if bruto is not None and liquido is not None and (inss or irrf):
            expected = bruto - (inss or Decimal("0")) - (irrf or Decimal("0"))
            if abs(expected - liquido) > Decimal("1.00"):
                warnings.append(
                    f"Contracheque: bruto {bruto} - inss {inss or 0} - irrf {irrf or 0} "
                    f"= {expected}, mas líquido lido é {liquido}"
                )


def _first_decimal(entries: list[ExtractedField] | None) -> Optional[Decimal]:
    if not entries:
        return None
    for e in entries:
        if isinstance(e.parsed, Decimal):
            return e.parsed
    return None


def analyze_text(
    pages_text: dict[int, list[str]],
) -> tuple[str, dict[str, list[ExtractedField]], list[str]]:
    """
    Flatten `pages_text` into one string, run the regex extractor, and return:
      (joined_clean_text, fields, warnings).

    Synchronous / regex-only path. For noise-tolerant extraction that also
    consults the local LLM, use `analyze_text_with_llm` (async).
    """
    from src.pdf_ocr.postprocessing.cleanup import cleanup_text

    joined = "\n".join(
        "\n".join(lines) for _, lines in sorted(pages_text.items())
    )
    clean = cleanup_text(joined)
    fields, warnings = ContextualExtractor().extract(clean)
    return clean, fields, warnings


async def analyze_text_with_llm(
    pages_text: dict[int, list[str]],
    llm_cfg=None,
) -> tuple[str, dict[str, list[ExtractedField]], list[str]]:
    """
    Regex pass + LLM structured-output pass. LLM value is kept only when
    regex is missing OR regex failed its validator. The clean text sent to
    the LLM is the same already produced by `analyze_text` — small, cheap,
    and offline (same LM Studio endpoint used for OCR).
    """
    from src.pdf_ocr.postprocessing.llm_extract import (
        DEFAULT_SCHEMA,
        LLMExtractConfig,
        llm_extract,
        merge_llm_with_regex,
    )

    clean, fields, warnings = analyze_text(pages_text)
    cfg = llm_cfg or LLMExtractConfig()
    llm_json = await llm_extract(clean, cfg)
    if llm_json:
        fields = merge_llm_with_regex(
            fields, llm_json, cfg.schema or DEFAULT_SCHEMA, warnings
        )
    return clean, fields, warnings
