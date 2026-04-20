"""
Fast per-page diagnostics used to decide which preprocessing ops to run.

All heuristics are pure OpenCV + NumPy, so they run in ~5-20 ms per page at
A4 200 DPI. No ML, no model load. Keep it that way — this module is the
cost floor of the preprocessing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class PageDiagnostics:
    skew_deg: float
    orientation_deg: int
    mean_lum: float
    contrast: float
    laplacian_var: float
    shadow_strength: float
    line_height_px: int
    is_low_contrast: bool
    is_noisy: bool
    is_shadowed: bool
    effective_dpi_floor_ok: bool


def diagnose(bgr: np.ndarray) -> PageDiagnostics:
    """Produce a PageDiagnostics for a BGR uint8 image."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr

    mean_lum = float(gray.mean())
    contrast = float(gray.std())

    _, inv = cv2.threshold(
        255 - gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    skew_deg = _estimate_skew(inv)
    orientation_deg = _estimate_orientation(inv)

    lap_var = float(cv2.Laplacian(cv2.GaussianBlur(gray, (3, 3), 0), cv2.CV_64F).var())

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (51, 51))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    shadow_strength = float(
        np.abs(gray.astype(np.float32) - bg.astype(np.float32)).mean()
    )

    line_height = _estimate_line_height(inv)

    return PageDiagnostics(
        skew_deg=skew_deg,
        orientation_deg=orientation_deg,
        mean_lum=mean_lum,
        contrast=contrast,
        laplacian_var=lap_var,
        shadow_strength=shadow_strength,
        line_height_px=line_height,
        is_low_contrast=(contrast < 40 or mean_lum < 80 or mean_lum > 210),
        is_noisy=lap_var > 1500,
        is_shadowed=shadow_strength > 12,
        effective_dpi_floor_ok=line_height >= 18,
    )


def _estimate_skew(binary_inv: np.ndarray) -> float:
    coords = np.column_stack(np.where(binary_inv > 0))
    if coords.shape[0] < 500:
        return 0.0
    # cv2.minAreaRect expects (x, y) pairs; np.where returns (row, col) = (y, x).
    angle = cv2.minAreaRect(coords[:, ::-1])[-1]
    if angle < -45:
        angle += 90
    elif angle > 45:
        angle -= 90
    # Clamp absurd values (happens on degenerate near-empty inputs).
    if abs(angle) > 45:
        return 0.0
    return float(angle)


def _estimate_orientation(binary_inv: np.ndarray) -> int:
    rows = binary_inv.sum(axis=1).astype(np.float32)
    cols = binary_inv.sum(axis=0).astype(np.float32)
    if rows.var() == 0 and cols.var() == 0:
        return 0
    return 0 if rows.var() >= cols.var() else 90


def _estimate_line_height(binary_inv: np.ndarray) -> int:
    """
    Median run of consecutive rows that contain ink. Approximates text line
    height in pixels. Used as a cheap proxy for effective DPI.
    """
    row_has_ink = (binary_inv.sum(axis=1) > 0).astype(np.uint8)
    if row_has_ink.sum() == 0:
        return 0
    runs: list[int] = []
    run = 0
    for v in row_has_ink:
        if v:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)
    if not runs:
        return 0
    return int(np.median(runs))
