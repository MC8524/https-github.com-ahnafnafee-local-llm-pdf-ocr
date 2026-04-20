"""
Schema-driven structured extraction using a local LLM (LM Studio / OpenAI
compatible). Runs as a SECOND pass AFTER regex — the goal is to survive
cosmetic variations that break regex:

  * extra whitespace / tabs / newlines before a value
  * a `/` or `-` punctuation that appears in one month's template and not
    the next
  * labels that spelled slightly differently across banks / employers
  * values split across two lines in one document and inline in another

The LLM receives the already-cleaned document text (no images — this pass
is text-only, so it is cheap and fast even on CPU) plus a schema describing
the fields to extract. It returns JSON. We merge with the regex extractor's
output via a deterministic rule:

  * Regex value wins when it is present AND passes its validator (CPF/CNPJ
    checksum, BRL parser).
  * LLM value wins when regex is missing.
  * When both present and disagree AND regex did NOT validate, the LLM
    value is used but a warning is emitted so the user can audit.

Offline guarantee: this module only talks to the same `AsyncOpenAI`-style
client used by `OCRProcessor`. Default points at `http://localhost:1234/v1`.
Nothing leaves the machine.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from src.pdf_ocr.postprocessing.schema import ExtractedField
from src.pdf_ocr.postprocessing.validators import (
    brl_to_decimal,
    cnpj_valid,
    cpf_valid,
    date_parse,
)


# Default schema covering contracheque + comprovante + DCTF receipt fields.
# Each entry: name -> (human description, type hint for the LLM, parser, validator).
DEFAULT_SCHEMA: dict[str, dict[str, str]] = {
    "cpf":          {"desc": "CPF do funcionário ou beneficiário (formato 000.000.000-00)", "type": "cpf"},
    "cnpj":         {"desc": "CNPJ da empresa emissora (formato 00.000.000/0000-00)", "type": "cnpj"},
    "nome":         {"desc": "Nome completo do funcionário/beneficiário", "type": "string"},
    "empresa":      {"desc": "Razão social da empresa emissora", "type": "string"},
    "competencia":  {"desc": "Competência/mês de referência no formato MM/YYYY", "type": "string"},
    "data":         {"desc": "Data principal do documento (emissão/pagamento) em DD/MM/YYYY", "type": "date"},
    "salario_bruto":{"desc": "Total bruto / total de proventos / vencimentos — apenas número, ponto de milhar e vírgula decimal", "type": "brl"},
    "inss":         {"desc": "Desconto de INSS — apenas número", "type": "brl"},
    "irrf":         {"desc": "Desconto de IRRF / Imposto de Renda — apenas número", "type": "brl"},
    "fgts":         {"desc": "FGTS depositado (informativo)", "type": "brl"},
    "liquido":      {"desc": "Líquido a receber / valor líquido — apenas número", "type": "brl"},
    "agencia":      {"desc": "Agência bancária", "type": "string"},
    "conta":        {"desc": "Número da conta corrente", "type": "string"},
    "banco":        {"desc": "Nome ou código do banco", "type": "string"},
    "valor":        {"desc": "Valor principal do comprovante (para comprovantes bancários)", "type": "brl"},
    "auth_code":    {"desc": "Código de autenticação bancária / hash do comprovante", "type": "string"},
    "pix_chave":    {"desc": "Chave PIX do favorecido (CPF, e-mail, telefone ou UUID)", "type": "string"},
    "dctf_recibo":  {"desc": "Número do recibo DCTF Web / recibo de declaração — aceita qualquer pontuação ao redor (/, -, espaços)", "type": "string"},
}


@dataclass
class LLMExtractConfig:
    schema: dict[str, dict[str, str]] = field(
        default_factory=lambda: dict(DEFAULT_SCHEMA)
    )
    model: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 1500
    # Cap the input text we send — if the doc is huge, we keep the head
    # (where labels and totals usually are) and the tail.
    max_input_chars: int = 8000


def _trim_text(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    head = text[: cap // 2]
    tail = text[-cap // 2 :]
    return f"{head}\n...[trecho omitido]...\n{tail}"


def _build_prompt(text: str, schema: dict[str, dict[str, str]]) -> str:
    schema_lines: list[str] = []
    for name, info in schema.items():
        schema_lines.append(f'  "{name}": "{info["desc"]} [{info["type"]}]"')
    schema_block = "{\n" + ",\n".join(schema_lines) + "\n}"
    return (
        "Você é um assistente que extrai campos estruturados de documentos "
        "fiscais brasileiros (contracheques, comprovantes bancários, DCTF Web, "
        "recibos de declaração). Leia o texto e retorne APENAS um objeto JSON "
        "com os campos listados abaixo. Regras:\n"
        "- Se o campo não aparecer no documento, use null.\n"
        "- Para campos `brl`, devolva apenas o número no formato `1234.56` "
        "(ponto decimal, sem 'R$', sem separador de milhar).\n"
        "- Para `date`, use `DD/MM/YYYY`.\n"
        "- Para `cpf` e `cnpj`, devolva com a pontuação original do documento.\n"
        "- Ignore espaços extras, traços e barras cosméticas ao redor dos "
        "valores — extraia o conteúdo real do campo.\n"
        "- NÃO explique. NÃO retorne markdown. Apenas o JSON cru.\n"
        "\nSchema:\n"
        f"{schema_block}\n"
        "\nTexto do documento:\n"
        f"{text}\n"
        "\nResposta JSON:"
    )


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def _parse_json_response(raw: str) -> dict[str, Any]:
    """Tolerant JSON parse — models sometimes wrap in ```json ... ```."""
    if not raw:
        return {}
    raw = raw.strip()
    # Strip markdown fences.
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_OBJECT_RE.search(raw)
        if not m:
            return {}
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            logging.warning("LLM extract: could not parse JSON: %s", raw[:200])
            return {}


async def llm_extract(
    text: str,
    cfg: Optional[LLMExtractConfig] = None,
) -> dict[str, Any]:
    """
    Send `text` to the local LLM with the extraction schema and return the
    parsed JSON dict. Keys match `cfg.schema`. Values are strings or None.
    """
    from openai import AsyncOpenAI  # lazy import

    cfg = cfg or LLMExtractConfig()
    base_url = cfg.api_base or os.getenv("LLM_API_BASE", "http://localhost:1234/v1")
    model_name = cfg.model or os.getenv("LLM_MODEL", "allenai/olmocr-2-7b")
    client = AsyncOpenAI(base_url=base_url, api_key="lm-studio")

    prompt = _build_prompt(_trim_text(text, cfg.max_input_chars), cfg.schema)
    try:
        resp = await client.chat.completions.create(
            model=model_name,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logging.warning("LLM extract: call failed: %s", e)
        return {}
    return _parse_json_response(raw)


def _parse_by_type(value: str, type_hint: str) -> tuple[Any, Optional[bool]]:
    """Parse an LLM-provided string by the schema type. Returns (parsed, valid)."""
    if value is None or value == "":
        return None, None
    s = str(value).strip()
    if type_hint == "cpf":
        return s, cpf_valid(s)
    if type_hint == "cnpj":
        return s, cnpj_valid(s)
    if type_hint == "brl":
        return _parse_brl_flexible(s), None
    if type_hint == "date":
        return date_parse(s), None
    return s, None


def _parse_brl_flexible(s: str):
    """
    Accept either ISO (1234.56) or BR (1.234,56) decimal formats. The LLM
    may normalize to ISO even when the document used BR.
    """
    from decimal import Decimal, InvalidOperation

    s = str(s).strip().replace("R$", "").replace(" ", "")
    if not s:
        return None
    has_comma = "," in s
    has_dot = "." in s
    try:
        if has_comma and has_dot:
            # BR format: dots are thousands, comma is decimal.
            return Decimal(s.replace(".", "").replace(",", "."))
        if has_comma:
            # comma decimal, no thousands.
            return Decimal(s.replace(",", "."))
        # dot-decimal OR integer.
        return Decimal(s)
    except InvalidOperation:
        return None


def merge_llm_with_regex(
    regex_fields: dict[str, list[ExtractedField]],
    llm_json: dict[str, Any],
    schema: dict[str, dict[str, str]],
    warnings: list[str],
) -> dict[str, list[ExtractedField]]:
    """
    Merge rules (LLM as a SUPPLEMENT, not a replacement):

    1. Regex-validated field present  → keep regex value.
    2. Regex present but validator failed AND LLM has a different value
       → keep LLM value, emit warning (audit trail).
    3. Regex missing, LLM present     → insert LLM value (marked valid=None).
    4. Both missing                   → skip.
    """
    merged = {k: list(v) for k, v in regex_fields.items()}
    for name, info in schema.items():
        type_hint = info.get("type", "string")
        llm_value = llm_json.get(name)
        if llm_value in (None, "", "null"):
            continue
        parsed, valid = _parse_by_type(llm_value, type_hint)

        # Map schema names to regex names where they differ.
        regex_name = _schema_to_regex_name(name)
        existing = merged.get(regex_name) or []

        if existing:
            primary = existing[0]
            # Case 1: regex validated → trust regex.
            if primary.valid is True:
                continue
            # Case 2: regex failed validator → prefer LLM if different.
            if primary.valid is False and str(llm_value).strip() != primary.value:
                warnings.append(
                    f"Divergência em `{name}`: regex='{primary.value}' "
                    f"(checksum falhou), LLM='{llm_value}' — usando LLM."
                )
                merged[regex_name] = [
                    ExtractedField(
                        name=regex_name,
                        value=str(llm_value),
                        parsed=parsed,
                        valid=valid,
                        source_line="<LLM fallback>",
                    ),
                    *existing,
                ]
                continue
            # Case where regex had no validator (e.g. BRL labeled fields):
            # If parsed decimals match, all good — append LLM as confirmation.
            if primary.parsed is not None and parsed is not None and primary.parsed == parsed:
                continue
            # Disagree on BRL without validator → warn but keep regex.
            if primary.parsed is not None and parsed is not None:
                warnings.append(
                    f"Divergência em `{name}`: regex='{primary.value}' "
                    f"(={primary.parsed}), LLM='{llm_value}' (={parsed})."
                )
            continue

        # Case 3: regex missing, LLM present.
        merged.setdefault(regex_name, []).append(
            ExtractedField(
                name=regex_name,
                value=str(llm_value),
                parsed=parsed,
                valid=valid,
                source_line="<LLM only>",
            )
        )

    return merged


def _schema_to_regex_name(schema_name: str) -> str:
    """
    Map schema field names to the regex extractor's field names where
    they differ.
    """
    mapping = {
        "data": "date",
        "valor": "brl",
        "pix_chave": "pix_uuid",  # regex has separate pix_* buckets; use UUID as canonical
    }
    return mapping.get(schema_name, schema_name)


__all__ = [
    "DEFAULT_SCHEMA",
    "LLMExtractConfig",
    "llm_extract",
    "merge_llm_with_regex",
]
