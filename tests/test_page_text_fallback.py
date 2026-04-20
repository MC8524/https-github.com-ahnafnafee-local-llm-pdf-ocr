"""
Digital short-circuit: when a PDF already has a usable text layer, the
pipeline should skip Surya detection AND LLM OCR for that page.

This is the single biggest speed win for the "pseudo-scanned" DCTF-style
PDFs (saved from a bad print driver) — those still carry the real text.
"""

from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest

from src.pdf_ocr.core.pdf import PDFHandler
from src.pdf_ocr.pipeline import OCRPipeline


def _make_digital_pdf(tmp_path: Path) -> Path:
    """Build a minimal single-page PDF that carries a real text layer."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    # Repeat the contracheque content to cover >= 10% of the page area so the
    # has_embedded_text() heuristic fires.
    body = (
        "EMPRESA ACME LTDA\nCNPJ: 11.222.333/0001-81\n"
        "Funcionário: João da Silva\nCPF: 529.982.247-25\n"
        "Competência: 04/2024\nSalário Bruto: R$ 2.500,00\n"
        "INSS: R$ 225,00\nIRRF: R$ 75,00\n"
        "Líquido a receber: R$ 2.200,00\n"
    )
    page.insert_text(
        (72, 72),
        body * 5,
        fontsize=11,
        fontname="helv",
    )
    path = tmp_path / "digital.pdf"
    doc.save(str(path))
    doc.close()
    return path


class StubAligner:
    """Tracks whether detection was invoked."""

    def __init__(self):
        self.detect_calls = 0
        self.align_calls = 0

    def get_detected_boxes_batch(self, image_bytes_list):
        self.detect_calls += 1
        return [[] for _ in image_bytes_list]

    def align_text(self, structured, llm_lines):
        self.align_calls += 1
        return structured


class StubOCR:
    def __init__(self):
        self.page_calls = 0
        self.crop_calls = 0

    async def perform_ocr(self, image_base64: str):
        self.page_calls += 1
        return ["stubbed"]

    async def perform_ocr_on_crop(self, image_base64: str):
        self.crop_calls += 1
        return "stub"


class TestHasEmbeddedText:
    def test_digital_pdf_detected(self, tmp_path):
        path = _make_digital_pdf(tmp_path)
        doc = fitz.open(path)
        assert PDFHandler.has_embedded_text(doc[0]) is True
        doc.close()

    def test_short_text_rejected(self, tmp_path):
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "hi", fontsize=11)
        path = tmp_path / "tiny.pdf"
        doc.save(str(path))
        doc.close()

        doc = fitz.open(path)
        assert PDFHandler.has_embedded_text(doc[0]) is False
        doc.close()


class TestPipelineShortCircuit:
    @pytest.mark.asyncio
    async def test_digital_page_skips_ocr(self, tmp_path):
        pdf = _make_digital_pdf(tmp_path)
        out_pdf = tmp_path / "out.pdf"

        aligner = StubAligner()
        ocr = StubOCR()

        # A no-op postprocessor ensures the with-text conversion path is taken
        # (pipeline only requests embedded text when a preprocessor OR
        # postprocessor is set).
        def noop_post(pages_text):
            return ("", {}, [])

        pipeline = OCRPipeline(
            aligner=aligner,
            ocr_processor=ocr,
            pdf_handler=PDFHandler(),
            text_postprocessor=noop_post,
        )
        result = await pipeline.run(str(pdf), str(out_pdf), dpi=100, refine=False)

        assert ocr.page_calls == 0, "LLM should NOT be called for digital pages"
        assert aligner.detect_calls == 0, "Surya should NOT run for digital pages"
        # pages_text should still carry the embedded text.
        assert 0 in result
        assert any("ACME" in line for line in result[0])

    @pytest.mark.asyncio
    async def test_image_only_page_still_runs_ocr(self, tmp_path):
        # Build a PDF whose single page has NO text layer (just a drawing).
        doc = fitz.open()
        page = doc.new_page(width=200, height=200)
        page.draw_rect(fitz.Rect(10, 10, 190, 190), color=(0, 0, 0), width=2)
        path = tmp_path / "image_only.pdf"
        doc.save(str(path))
        doc.close()

        aligner = StubAligner()
        ocr = StubOCR()

        def noop_post(pages_text):
            return ("", {}, [])

        pipeline = OCRPipeline(
            aligner=aligner,
            ocr_processor=ocr,
            pdf_handler=PDFHandler(),
            text_postprocessor=noop_post,
        )
        await pipeline.run(str(path), str(tmp_path / "out.pdf"), dpi=100, refine=False)
        assert ocr.page_calls == 1
        assert aligner.detect_calls == 1
