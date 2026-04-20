"""
Preprocessing operations. Each function takes and returns a BGR uint8 ndarray.

Keep these pure and side-effect-free — the composer in `pipeline.py` decides
which ones to call based on `PageDiagnostics`.
"""

from __future__ import annotations

import cv2
import numpy as np


def rotate_90(bgr: np.ndarray, orientation_deg: int) -> np.ndarray:
    """Fix obvious 90°/270° rotation before skew detection."""
    if orientation_deg == 90:
        return np.ascontiguousarray(np.rot90(bgr, k=-1))
    if orientation_deg == 270:
        return np.ascontiguousarray(np.rot90(bgr, k=1))
    return bgr


def deskew(bgr: np.ndarray, angle_deg: float) -> np.ndarray:
    if abs(angle_deg) < 0.7:
        return bgr
    h, w = bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    return cv2.warpAffine(
        bgr, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def clahe_contrast(bgr: np.ndarray) -> np.ndarray:
    """CLAHE on the L channel of LAB — contrast without color shift."""
    if bgr.ndim == 2:
        return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(bgr)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def shadow_flatten(bgr: np.ndarray) -> np.ndarray:
    """
    Remove background gradient from phone-scanned pages. Divide the image by
    its large-kernel morphological close — the close approximates the paper
    background, and dividing cancels it out.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (51, 51))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    # Guard against divide-by-zero on completely black inputs.
    bg = np.maximum(bg, 1)
    flat = cv2.divide(gray, bg, scale=255)
    return cv2.cvtColor(flat, cv2.COLOR_GRAY2BGR)


def denoise_light(bgr: np.ndarray) -> np.ndarray:
    """fastNlMeansDenoising on the gray channel — keeps shape 3-channel."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr
    dn = cv2.fastNlMeansDenoising(
        gray, None,
        h=7, templateWindowSize=7, searchWindowSize=21,
    )
    return cv2.cvtColor(dn, cv2.COLOR_GRAY2BGR)


def upscale_to_dpi_floor(bgr: np.ndarray, target_longest: int = 2000) -> np.ndarray:
    """Only upscale — never downscale. Preserves small text pages for OCR."""
    h, w = bgr.shape[:2]
    longest = max(h, w)
    if longest >= target_longest:
        return bgr
    scale = target_longest / longest
    return cv2.resize(
        bgr, (int(w * scale), int(h * scale)),
        interpolation=cv2.INTER_CUBIC,
    )


def adaptive_binarize(bgr: np.ndarray) -> np.ndarray:
    """
    Rescue-path only. OpenCV adaptiveThreshold is close enough to Sauvola
    without needing scikit-image. Output is 3-channel so downstream code
    that expects BGR keeps working.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr
    bw = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 12,
    )
    return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
