"""
Conditional preprocessing pipeline — the "truly intelligent" composer.

Takes a BGR image, diagnoses it, and applies only the ops that address
the specific defects detected. Default mode ("auto") is aggressive enough
to recover noisy phone scans but cheap on clean pages (most ops skipped).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from src.pdf_ocr.preprocessing.classify import PageDiagnostics, diagnose
from src.pdf_ocr.preprocessing.operations import (
    adaptive_binarize,
    clahe_contrast,
    denoise_light,
    deskew,
    rotate_90,
    shadow_flatten,
    upscale_to_dpi_floor,
)


@dataclass(frozen=True)
class PreprocessConfig:
    mode: str = "auto"            # "auto" | "off" | "aggressive"
    dpi_floor_px: int = 2000      # longest-edge target when upscaling
    max_threads: int = 4          # used by the PDFHandler threadpool


def run_preprocess(
    bgr: np.ndarray,
    cfg: PreprocessConfig,
) -> tuple[np.ndarray, Optional[PageDiagnostics]]:
    """
    Apply a conditional sequence of ops chosen by the per-page classifier.

    Returns (processed_bgr, diagnostics). `mode="off"` returns the input
    unchanged with `None` diagnostics — callers can use this as a sentinel.
    """
    if cfg.mode == "off":
        return bgr, None

    diag = diagnose(bgr)
    out = bgr

    # 1. Upright a 90°/270° page before skew estimation.
    if diag.orientation_deg in (90, 270):
        out = rotate_90(out, diag.orientation_deg)

    # 2. Deskew only when it meaningfully crooked.
    if abs(diag.skew_deg) >= 0.7:
        out = deskew(out, diag.skew_deg)

    # 3. Flatten paper-background shadow before CLAHE, else CLAHE amplifies it.
    if diag.is_shadowed:
        out = shadow_flatten(out)

    # 4. CLAHE for faded scans.
    if diag.is_low_contrast:
        out = clahe_contrast(out)

    # 5. Denoise only when necessary — it's the slowest op.
    if diag.is_noisy:
        out = denoise_light(out)

    # 6. DPI floor: never downscale, only upscale if text looks tiny.
    if not diag.effective_dpi_floor_ok:
        out = upscale_to_dpi_floor(out, target_longest=cfg.dpi_floor_px)

    # 7. Aggressive rescue: binarize only if contrast is still terrible.
    if cfg.mode == "aggressive":
        post_gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY) if out.ndim == 3 else out
        if float(post_gray.std()) < 35:
            out = adaptive_binarize(out)

    return out, diag


def preprocess_crop_bgr(
    bgr: np.ndarray,
    cfg: PreprocessConfig | None = None,
) -> np.ndarray:
    """
    Lightweight subset for crop-stage re-OCR: shadow-flatten, CLAHE, upscale.
    No deskew (crops are already axis-aligned) and no denoise (tiny crops
    don't have enough pixels to estimate noise meaningfully).
    """
    cfg = cfg or PreprocessConfig()
    if cfg.mode == "off":
        return bgr
    out = bgr
    gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY) if out.ndim == 3 else out
    if float(gray.std()) < 40:
        out = clahe_contrast(out)
    return out
