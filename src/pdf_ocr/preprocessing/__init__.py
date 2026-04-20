"""Per-page adaptive image preprocessing."""

from src.pdf_ocr.preprocessing.classify import PageDiagnostics, diagnose
from src.pdf_ocr.preprocessing.pipeline import (
    PreprocessConfig,
    preprocess_crop_bgr,
    run_preprocess,
)

__all__ = [
    "PageDiagnostics",
    "diagnose",
    "PreprocessConfig",
    "run_preprocess",
    "preprocess_crop_bgr",
]
