"""
Local LLM PDF OCR - Package for OCR processing using local vision models.

Converts scanned PDFs into searchable documents using local vision LLMs
for text extraction and Surya for layout detection.
"""

__version__ = "1.0.0"

from src.pdf_ocr.api import analyze_document
from src.pdf_ocr.core.aligner import HybridAligner
from src.pdf_ocr.core.grounded import (
    DEFAULT_GROUNDING_PROMPT,
    GroundedBlock,
    GroundedOCRBackend,
    GroundedResponse,
    PromptedGroundedOCR,
    ZAIHostedOCR,
    parse_glm_layout_details,
    parse_zai_response,
)
from src.pdf_ocr.core.ocr import OCRProcessor
from src.pdf_ocr.core.pdf import PDFHandler
from src.pdf_ocr.pipeline import OCRPipeline, parse_page_range
from src.pdf_ocr.postprocessing import (
    DEFAULT_SCHEMA,
    ContextualExtractor,
    DocumentResult,
    ExtractedField,
    LLMExtractConfig,
    analyze_text,
    analyze_text_with_llm,
    brl_to_decimal,
    cnpj_valid,
    cpf_valid,
    date_parse,
    llm_extract,
    merge_llm_with_regex,
)
from src.pdf_ocr.preprocessing import (
    PageDiagnostics,
    PreprocessConfig,
    diagnose,
    preprocess_crop_bgr,
    run_preprocess,
)

__all__ = [
    "PDFHandler",
    "OCRProcessor",
    "HybridAligner",
    "OCRPipeline",
    "GroundedBlock",
    "GroundedResponse",
    "GroundedOCRBackend",
    "PromptedGroundedOCR",
    "ZAIHostedOCR",
    "DEFAULT_GROUNDING_PROMPT",
    "parse_zai_response",
    "parse_glm_layout_details",
    "parse_page_range",
    # Preprocessing
    "PreprocessConfig",
    "PageDiagnostics",
    "diagnose",
    "run_preprocess",
    "preprocess_crop_bgr",
    # Postprocessing
    "DocumentResult",
    "ExtractedField",
    "ContextualExtractor",
    "analyze_text",
    "analyze_text_with_llm",
    "cpf_valid",
    "cnpj_valid",
    "brl_to_decimal",
    "date_parse",
    "DEFAULT_SCHEMA",
    "LLMExtractConfig",
    "llm_extract",
    "merge_llm_with_regex",
    # High-level API
    "analyze_document",
    "__version__",
]
