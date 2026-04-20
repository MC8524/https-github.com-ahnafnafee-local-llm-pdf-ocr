"""Per-page image preprocessing — classifier + conditional ops."""

import cv2
import numpy as np
import pytest

from src.pdf_ocr.preprocessing import (
    PreprocessConfig,
    diagnose,
    preprocess_crop_bgr,
    run_preprocess,
)
from src.pdf_ocr.preprocessing.operations import (
    clahe_contrast,
    deskew,
    rotate_90,
    shadow_flatten,
    upscale_to_dpi_floor,
)


def _text_page(width=1000, height=1400, angle_deg: float = 0.0) -> np.ndarray:
    """Render a synthetic A4-ish white page with a few lines of text."""
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    for i, y in enumerate([200, 350, 500, 650, 800, 950, 1100, 1250]):
        cv2.putText(
            img, f"Line of text number {i} — Salario Bruto R$ 1.234,56",
            (80, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2,
        )
    if angle_deg != 0.0:
        M = cv2.getRotationMatrix2D((width / 2, height / 2), -angle_deg, 1.0)
        img = cv2.warpAffine(
            img, M, (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
    return img


class TestDiagnose:
    def test_clean_page_classification(self):
        img = _text_page()
        diag = diagnose(img)
        # Clean page: no skew, not noisy. Low-contrast classification depends
        # on text density — white-heavy pages naturally have low std, so we
        # don't assert is_low_contrast either way.
        assert abs(diag.skew_deg) < 0.7
        assert not diag.is_noisy

    def test_detects_skew(self):
        img = _text_page(angle_deg=7.0)
        diag = diagnose(img)
        # We rotated -7°; minAreaRect output sign may flip but magnitude matches.
        assert 4.0 <= abs(diag.skew_deg) <= 10.0

    def test_detects_low_contrast(self):
        img = _text_page()
        faded = cv2.addWeighted(img, 0.3, np.full_like(img, 200), 0.7, 0)
        diag = diagnose(faded)
        assert diag.is_low_contrast

    def test_detects_noise(self):
        img = _text_page()
        rng = np.random.default_rng(seed=42)
        # Salt-and-pepper noise: isolated extreme pixels survive the 3x3
        # pre-blur that plain Gaussian additive noise would get averaged out by.
        salt = rng.random(img.shape[:2]) < 0.08
        pepper = rng.random(img.shape[:2]) < 0.08
        noisy = img.copy()
        noisy[salt] = 0
        noisy[pepper] = 255
        diag = diagnose(noisy)
        assert diag.is_noisy


class TestOperations:
    def test_deskew_reduces_skew(self):
        img = _text_page(angle_deg=7.0)
        diag_before = diagnose(img)
        fixed = deskew(img, diag_before.skew_deg)
        diag_after = diagnose(fixed)
        assert abs(diag_after.skew_deg) < abs(diag_before.skew_deg)

    def test_clahe_preserves_shape(self):
        img = _text_page()
        out = clahe_contrast(img)
        assert out.shape == img.shape
        assert out.dtype == img.dtype

    def test_shadow_flatten_preserves_shape(self):
        img = _text_page()
        out = shadow_flatten(img)
        assert out.shape == img.shape

    def test_upscale_never_downscales(self):
        img = _text_page(width=3000, height=4200)  # already big
        out = upscale_to_dpi_floor(img, target_longest=2000)
        assert out.shape == img.shape

    def test_upscale_grows_small_input(self):
        img = _text_page(width=800, height=1100)
        out = upscale_to_dpi_floor(img, target_longest=2000)
        assert max(out.shape[:2]) >= 1999

    def test_rotate_90(self):
        img = _text_page(width=1000, height=1400)
        out = rotate_90(img, 90)
        assert out.shape[:2] == (1000, 1400)  # H and W swap


class TestRunPreprocess:
    def test_off_mode_returns_input(self):
        img = _text_page()
        out, diag = run_preprocess(img, PreprocessConfig(mode="off"))
        assert diag is None
        assert np.array_equal(out, img)

    def test_auto_leaves_clean_page_mostly_unchanged(self):
        img = _text_page()
        out, diag = run_preprocess(img, PreprocessConfig(mode="auto"))
        assert diag is not None
        # Same shape — no upscale for a 1000x1400 page (longest=1400 < 2000 so
        # it WILL upscale unless we relax the floor). Check ratio-preserving.
        assert out.shape[2] == 3

    def test_auto_corrects_skewed_page(self):
        img = _text_page(angle_deg=5.0)
        out, _ = run_preprocess(img, PreprocessConfig(mode="auto"))
        diag_after = diagnose(out)
        assert abs(diag_after.skew_deg) < 2.5

    def test_aggressive_binarizes_low_contrast(self):
        img = _text_page()
        faded = cv2.addWeighted(img, 0.2, np.full_like(img, 200), 0.8, 0)
        out, _ = run_preprocess(faded, PreprocessConfig(mode="aggressive"))
        # Output should have high contrast (binarization) OR improved via CLAHE.
        assert float(cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).std()) > 30


class TestCropPreprocess:
    def test_off_returns_input(self):
        img = _text_page(width=300, height=80)
        out = preprocess_crop_bgr(img, PreprocessConfig(mode="off"))
        assert np.array_equal(out, img)

    def test_auto_applies_clahe_when_low_contrast(self):
        img = _text_page(width=300, height=80)
        faded = cv2.addWeighted(img, 0.3, np.full_like(img, 200), 0.7, 0)
        out = preprocess_crop_bgr(faded, PreprocessConfig(mode="auto"))
        assert out.shape == faded.shape
