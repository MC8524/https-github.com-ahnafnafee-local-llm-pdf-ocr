"""Post-OCR text cleanup and Brazilian fiscal field extraction."""

from src.pdf_ocr.postprocessing.cleanup import (
    cleanup_text,
    dehyphenate,
    fix_numeric_confusion,
    fix_rn_confusion,
    normalize_whitespace,
)
from src.pdf_ocr.postprocessing.extractors import (
    ContextualExtractor,
    analyze_text,
    analyze_text_with_llm,
)
from src.pdf_ocr.postprocessing.llm_extract import (
    DEFAULT_SCHEMA,
    LLMExtractConfig,
    llm_extract,
    merge_llm_with_regex,
)
from src.pdf_ocr.postprocessing.schema import DocumentResult, ExtractedField
from src.pdf_ocr.postprocessing.validators import (
    brl_to_decimal,
    cnpj_valid,
    cpf_valid,
    date_parse,
)

__all__ = [
    "DocumentResult",
    "ExtractedField",
    "ContextualExtractor",
    "analyze_text",
    "analyze_text_with_llm",
    "cleanup_text",
    "dehyphenate",
    "fix_numeric_confusion",
    "fix_rn_confusion",
    "normalize_whitespace",
    "cpf_valid",
    "cnpj_valid",
    "brl_to_decimal",
    "date_parse",
    "llm_extract",
    "merge_llm_with_regex",
    "LLMExtractConfig",
    "DEFAULT_SCHEMA",
]
