"""
LLM structured extraction — merge rules and tolerance to cosmetic noise.

Uses a stubbed LLM client (monkeypatched at the AsyncOpenAI layer) so these
tests run fully offline without LM Studio.
"""

from decimal import Decimal

import pytest

from src.pdf_ocr.postprocessing import (
    DEFAULT_SCHEMA,
    ContextualExtractor,
    LLMExtractConfig,
    analyze_text_with_llm,
    merge_llm_with_regex,
)
from src.pdf_ocr.postprocessing.llm_extract import _parse_json_response


class TestJSONParse:
    def test_plain_json(self):
        assert _parse_json_response('{"a": 1}') == {"a": 1}

    def test_markdown_wrapped(self):
        raw = "```json\n{\"a\": 1}\n```"
        assert _parse_json_response(raw) == {"a": 1}

    def test_extra_prose(self):
        raw = 'Here is the extraction:\n{"a": 1}\nThanks!'
        assert _parse_json_response(raw) == {"a": 1}

    def test_malformed(self):
        assert _parse_json_response("no json here") == {}


class TestMergeRules:
    def test_regex_valid_wins_over_llm(self):
        regex_fields, _ = ContextualExtractor().extract(
            "CPF: 529.982.247-25"
        )
        llm = {"cpf": "111.111.111-11"}
        merged = merge_llm_with_regex(regex_fields, llm, DEFAULT_SCHEMA, warnings=[])
        # Regex-validated CPF stays.
        assert merged["cpf"][0].value == "529.982.247-25"
        assert merged["cpf"][0].valid is True

    def test_llm_fills_missing(self):
        regex_fields, _ = ContextualExtractor().extract(
            "documento sem cpf nem cnpj"
        )
        llm = {"nome": "João da Silva", "liquido": "2200.00"}
        merged = merge_llm_with_regex(regex_fields, llm, DEFAULT_SCHEMA, warnings=[])
        assert merged["nome"][0].value == "João da Silva"
        # The schema type for `liquido` is brl, but merger accepts dot-decimal.
        assert merged["liquido"][0].parsed == Decimal("2200.00")

    def test_llm_wins_when_regex_invalid(self):
        regex_fields, _ = ContextualExtractor().extract(
            "CPF: 111.111.111-11"   # invalid checksum
        )
        llm = {"cpf": "529.982.247-25"}
        warnings: list[str] = []
        merged = merge_llm_with_regex(regex_fields, llm, DEFAULT_SCHEMA, warnings)
        assert merged["cpf"][0].value == "529.982.247-25"
        assert merged["cpf"][0].valid is True
        assert any("Divergência em `cpf`" in w for w in warnings)

    def test_slash_variation_handled_by_llm(self):
        # Regex DCTF_RECIBO_RE expects `recibo` label directly followed by the
        # number. If a stray `/` breaks that, regex misses — but LLM finds it.
        regex_fields, _ = ContextualExtractor().extract(
            "Número do recibo: / ABC123DEF456"
        )
        # Regex here actually captures the code because our pattern is
        # tolerant; the real-world scenario is variable, so the key test is
        # that when regex misses, the LLM fills it.
        regex_fields.pop("dctf_recibo", None)
        llm = {"dctf_recibo": "ABC123DEF456"}
        merged = merge_llm_with_regex(regex_fields, llm, DEFAULT_SCHEMA, warnings=[])
        assert merged["dctf_recibo"][0].value == "ABC123DEF456"


class TestAnalyzeTextWithLLM:
    @pytest.mark.asyncio
    async def test_stubbed_llm_merges_cleanly(self, monkeypatch):
        """End-to-end: regex + LLM merge, LM Studio replaced by a stub."""
        import sys

        # The parent package re-exports `llm_extract` as a function, shadowing
        # the submodule attribute. Pull the module from sys.modules instead.
        mod = sys.modules["src.pdf_ocr.postprocessing.llm_extract"]

        async def fake_llm_extract(text, cfg=None):
            # Pretend the LLM found the fields regex missed.
            return {
                "cpf": "529.982.247-25",
                "nome": "Maria Teste",
                "liquido": "1500.00",
                "dctf_recibo": "REC-2024-001",
            }

        monkeypatch.setattr(mod, "llm_extract", fake_llm_extract)

        pages = {
            0: [
                "Folha de Pagamento - Abril/2024",
                "Funcionário: Maria Teste",
            ]
        }
        text, fields, warnings = await analyze_text_with_llm(
            pages, LLMExtractConfig()
        )
        assert fields["cpf"][0].value == "529.982.247-25"
        assert fields["cpf"][0].valid is True
        assert fields["nome"][0].value == "Maria Teste"
        assert fields["dctf_recibo"][0].value == "REC-2024-001"
