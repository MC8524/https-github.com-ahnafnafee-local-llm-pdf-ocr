"""
High-level entry point: `analyze_document(...)`.

Designed to be called from the user's "analyze each company" script:

    import asyncio
    from src.pdf_ocr import analyze_document

    result = asyncio.run(analyze_document("contracheque_abril.pdf"))
    for cpf in result.fields.get("cpf", []):
        print(cpf.value, "válido?" , cpf.valid)
    print("líquido:", result.first_decimal("liquido"))
    for w in result.warnings:
        print("WARN:", w)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.pdf_ocr.postprocessing import (
    DocumentResult,
    LLMExtractConfig,
    analyze_text,
    analyze_text_with_llm,
)
from src.pdf_ocr.preprocessing import PreprocessConfig, preprocess_crop_bgr, run_preprocess


async def analyze_document(
    pdf_path: str,
    output_path: Optional[str] = None,
    *,
    preprocess: str = "auto",
    extract_fields: bool = True,
    llm_extract: bool = False,
    llm_extract_model: Optional[str] = None,
    dpi: int = 200,
    concurrency: int = 3,
    max_image_dim: int = 1024,
    api_base: Optional[str] = None,
    model: Optional[str] = None,
    refine: bool = True,
) -> DocumentResult:
    """
    Rasterize → preprocess → Surya detect → local LLM OCR → refine →
    cleanup → extract Brazilian fiscal fields. Returns a DocumentResult.

    Args:
        pdf_path: Path to a PDF or image file.
        output_path: Where to write the searchable PDF. Defaults to
            `<pdf_stem>_ocr.pdf` next to the input.
        preprocess: "auto" | "off" | "aggressive".
        extract_fields: When False, skips cleanup/extraction — DocumentResult
            carries only raw text and the output PDF path.
        llm_extract: When True, runs a schema-driven second pass through the
            local LLM on the cleaned text (text-only, fast). Merges with the
            regex extractor so regex wins for validated fields (CPF/CNPJ
            checksum) and LLM fills in gaps where cosmetic variation broke
            the regex. Requires `extract_fields=True`.
        llm_extract_model: Override the model used for the LLM extract pass.
            Defaults to the same OCR model (`model` / LLM_MODEL env var).
        dpi / concurrency / max_image_dim / refine: forwarded to OCRPipeline.
        api_base / model: override LLM endpoint (defaults to `.env`).
    """
    # Import heavy modules lazily so the API surface doesn't pay Surya
    # model-load cost at module-import time.
    from src.pdf_ocr.core.aligner import HybridAligner
    from src.pdf_ocr.core.ocr import OCRProcessor
    from src.pdf_ocr.core.pdf import PDFHandler
    from src.pdf_ocr.pipeline import OCRPipeline

    cfg = PreprocessConfig(mode=preprocess)

    def image_preprocessor(bgr, *, page_num: int):
        out, _diag = run_preprocess(bgr, cfg)
        return out

    def crop_preprocessor(bgr):
        return preprocess_crop_bgr(bgr, cfg)

    text_postprocessor = None
    if extract_fields:
        if llm_extract:
            llm_cfg = LLMExtractConfig(
                model=llm_extract_model or model,
                api_base=api_base,
            )
            async def text_postprocessor(pages_text):
                return await analyze_text_with_llm(pages_text, llm_cfg)
        else:
            text_postprocessor = analyze_text

    pipeline = OCRPipeline(
        aligner=HybridAligner(),
        ocr_processor=OCRProcessor(api_base=api_base, model=model),
        pdf_handler=PDFHandler(),
        image_preprocessor=image_preprocessor if preprocess != "off" else None,
        crop_preprocessor=crop_preprocessor if preprocess != "off" else None,
        text_postprocessor=text_postprocessor,
    )

    out_path = output_path or str(
        Path(pdf_path).with_name(f"{Path(pdf_path).stem}_ocr.pdf")
    )
    pages_text = await pipeline.run(
        pdf_path, out_path,
        dpi=dpi,
        concurrency=concurrency,
        refine=refine,
        max_image_dim=max_image_dim,
    )

    if pipeline.last_result is not None:
        return pipeline.last_result

    # Postprocessor disabled — return a minimal DocumentResult so callers
    # still get a uniform shape.
    flat = "\n".join(
        "\n".join(lines) for _, lines in sorted(pages_text.items())
    )
    return DocumentResult(
        text=flat,
        pages_text=pages_text,
        output_pdf=out_path,
    )
