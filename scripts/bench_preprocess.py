#!/usr/bin/env python3
"""
Benchmark preprocessing modes on the example PDFs.

Runs each mode ("off", "auto", "aggressive") end-to-end through the
diagnose() + run_preprocess() pipeline and reports per-page wall time.
Also runs the regex extractor on the OCR output to count extracted fields.

Requires a running local LLM (LM Studio) to cover the full path; pass
--no-ocr to benchmark the preprocessing ops alone.

Usage:
    uv run scripts/bench_preprocess.py
    uv run scripts/bench_preprocess.py --no-ocr
    uv run scripts/bench_preprocess.py --pdf examples/hybrid.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import io
import time
from pathlib import Path

import fitz
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent.parent


def _page_to_bgr(pdf_path: Path, page_index: int, dpi: int) -> np.ndarray:
    doc = fitz.open(pdf_path)
    try:
        pix = doc[page_index].get_pixmap(dpi=dpi)
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        if mode == "RGBA":
            img = img.convert("RGB")
        return np.asarray(img)[:, :, ::-1].copy()  # RGB -> BGR
    finally:
        doc.close()


def bench_preprocess_ops(pdf_path: Path, dpi: int = 200) -> None:
    from src.pdf_ocr.preprocessing import PreprocessConfig, run_preprocess

    doc = fitz.open(pdf_path)
    n_pages = len(doc)
    doc.close()

    print(f"\n=== {pdf_path.name} ({n_pages} pages @ {dpi} DPI) ===")
    for mode in ("off", "auto", "aggressive"):
        cfg = PreprocessConfig(mode=mode)
        timings: list[float] = []
        for i in range(n_pages):
            bgr = _page_to_bgr(pdf_path, i, dpi)
            t0 = time.perf_counter()
            run_preprocess(bgr, cfg)
            timings.append(time.perf_counter() - t0)
        avg_ms = 1000 * sum(timings) / max(1, len(timings))
        max_ms = 1000 * max(timings) if timings else 0.0
        print(f"  {mode:<11} avg={avg_ms:6.1f} ms/page  max={max_ms:6.1f} ms/page")


async def bench_full_pipeline(pdf_path: Path) -> None:
    from src.pdf_ocr import analyze_document

    for mode in ("off", "auto"):
        t0 = time.perf_counter()
        result = await analyze_document(
            str(pdf_path),
            output_path=str(pdf_path.with_suffix(f".bench_{mode}.pdf")),
            preprocess=mode,
            extract_fields=True,
        )
        elapsed = time.perf_counter() - t0
        n_cpf = len(result.fields.get("cpf", []))
        n_brl = len(result.fields.get("brl", []))
        n_warn = len(result.warnings)
        print(
            f"  {mode:<11} total={elapsed:6.2f}s  "
            f"cpf={n_cpf}  brl={n_brl}  warnings={n_warn}"
        )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", action="append", help="PDF to benchmark (can repeat)")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument(
        "--no-ocr", action="store_true",
        help="Only time preprocessing ops; do NOT call the LLM",
    )
    args = p.parse_args()

    pdfs = [Path(x) for x in args.pdf] if args.pdf else sorted(
        (ROOT / "examples").glob("*.pdf")
    )
    pdfs = [p for p in pdfs if "_ocr" not in p.stem and "bench_" not in p.stem]
    if not pdfs:
        raise SystemExit("No PDFs found to benchmark.")

    for pdf in pdfs:
        bench_preprocess_ops(pdf, dpi=args.dpi)

    if args.no_ocr:
        return

    print("\n=== Full pipeline (requires LM Studio running) ===")
    for pdf in pdfs:
        print(f"\n{pdf.name}")
        try:
            asyncio.run(bench_full_pipeline(pdf))
        except Exception as e:
            print(f"  [skipped — {e}]")


if __name__ == "__main__":
    main()
