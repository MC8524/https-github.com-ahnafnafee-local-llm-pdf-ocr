"""
PDFHandler - PDF processing utilities.

Handles PDF to image conversion and text embedding for creating searchable
PDFs. Also accepts raw image inputs (JPEG/PNG/TIFF/BMP) — including
multi-page TIFF — so single-scan-per-file workflows don't need a PDF wrap
step first.
"""

import base64
import io
from pathlib import Path
from typing import Callable, Optional

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageSequence


IMAGE_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp",
})


ImagePreprocessor = Callable[..., "np.ndarray"]
"""Signature: (bgr_ndarray, *, page_num: int) -> bgr_ndarray."""


def _is_image_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def _pixmap_to_bgr(pix: "fitz.Pixmap") -> "np.ndarray":
    """Convert a PyMuPDF pixmap to a BGR ndarray (what OpenCV expects)."""
    mode = "RGBA" if pix.alpha else "RGB"
    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    if mode == "RGBA":
        img = img.convert("RGB")
    arr = np.asarray(img)  # RGB
    return arr[:, :, ::-1].copy()  # BGR


def _bgr_to_base64_jpeg(
    bgr: "np.ndarray", *, max_dim: int, quality: int = 50
) -> str:
    img = Image.fromarray(bgr[:, :, ::-1])  # BGR -> RGB
    img.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class PDFHandler:
    """
    PDF processing handler for OCR workflows.

    Handles:
    - Converting PDF pages to base64 PNG images
    - Embedding an invisible text layer to produce a "sandwich" PDF
      (image background + selectable/searchable text overlay)
    """

    def convert_to_images(
        self,
        pdf_path,
        dpi: int = 150,
        max_image_dim: int = 1024,
        *,
        image_preprocessor: Optional[ImagePreprocessor] = None,
    ) -> dict[int, str]:
        """
        Render every page to a base64-encoded JPEG, capped at `max_image_dim`
        pixels on the longest edge so the image fits the VLM's context window.

        Accepts either a PDF or a raw image file (JPEG/PNG/TIFF/BMP/WebP).
        Multi-page TIFFs are expanded to one page per frame. For images the
        `dpi` argument is ignored — the file is used at its native resolution,
        capped by `max_image_dim`.

        Smaller caps are required by some local VLMs:
          - OlmOCR-2 (Qwen2.5-VL base): 1024 is fine (default)
          - GLM-OCR:1.1B (Ollama): ~640 — larger images crash the runner
          - Florence-2 / MinerU: see their docs

        When `image_preprocessor` is set, each page is passed through it as a
        BGR ndarray (OpenCV convention) between rasterization and JPEG encode.

        Returns a dict of {page_num: base64_str}.
        """
        if _is_image_path(pdf_path):
            return self._images_from_image_file(
                pdf_path, max_image_dim, image_preprocessor=image_preprocessor
            )

        images: dict[int, str] = {}
        doc = fitz.open(pdf_path)
        try:
            for page_num, page in enumerate(doc):
                pix = page.get_pixmap(dpi=dpi)
                if image_preprocessor is not None:
                    bgr = _pixmap_to_bgr(pix)
                    bgr = image_preprocessor(bgr, page_num=page_num)
                    images[page_num] = _bgr_to_base64_jpeg(
                        bgr, max_dim=max_image_dim, quality=50
                    )
                else:
                    img = Image.open(io.BytesIO(pix.tobytes("jpg", jpg_quality=50)))
                    img.thumbnail((max_image_dim, max_image_dim))
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=50)
                    images[page_num] = base64.b64encode(
                        buffer.getvalue()
                    ).decode("utf-8")
        finally:
            doc.close()
        return images

    def convert_to_images_with_text(
        self,
        pdf_path,
        dpi: int = 150,
        max_image_dim: int = 1024,
        *,
        image_preprocessor: Optional[ImagePreprocessor] = None,
        min_embedded_chars: int = 50,
        min_embedded_area_frac: float = 0.10,
    ) -> tuple[dict[int, str], dict[int, str]]:
        """
        Like `convert_to_images`, but also returns a dict of embedded text per
        page for pages that already have a usable text layer. Callers can
        short-circuit OCR entirely on those pages.

        Returns (images, embedded_text). `embedded_text[page_num]` is only
        present when the page's text layer passes the usability threshold
        (>= `min_embedded_chars` chars AND covers >= `min_embedded_area_frac`
        of the page area).

        Image inputs never carry a text layer, so `embedded_text` is always
        empty for those.
        """
        if _is_image_path(pdf_path):
            images = self._images_from_image_file(
                pdf_path, max_image_dim, image_preprocessor=image_preprocessor
            )
            return images, {}

        images: dict[int, str] = {}
        embedded: dict[int, str] = {}
        doc = fitz.open(pdf_path)
        try:
            for page_num, page in enumerate(doc):
                if self.has_embedded_text(
                    page,
                    min_chars=min_embedded_chars,
                    min_area_frac=min_embedded_area_frac,
                ):
                    embedded[page_num] = page.get_text("text") or ""
                pix = page.get_pixmap(dpi=dpi)
                if image_preprocessor is not None:
                    bgr = _pixmap_to_bgr(pix)
                    bgr = image_preprocessor(bgr, page_num=page_num)
                    images[page_num] = _bgr_to_base64_jpeg(
                        bgr, max_dim=max_image_dim, quality=50
                    )
                else:
                    img = Image.open(io.BytesIO(pix.tobytes("jpg", jpg_quality=50)))
                    img.thumbnail((max_image_dim, max_image_dim))
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=50)
                    images[page_num] = base64.b64encode(
                        buffer.getvalue()
                    ).decode("utf-8")
        finally:
            doc.close()
        return images, embedded

    @staticmethod
    def has_embedded_text(
        page,
        *,
        min_chars: int = 50,
        min_area_frac: float = 0.10,
    ) -> bool:
        """
        True when the PyMuPDF page carries a meaningful text layer.

        Dual threshold to avoid false positives on PDFs with only a watermark
        or footer text: requires both a character-count floor and an
        area-coverage floor.
        """
        text = page.get_text("text") or ""
        if len(text.strip()) < min_chars:
            return False
        page_area = page.rect.width * page.rect.height
        if page_area <= 0:
            return False
        covered = 0.0
        for b in page.get_text("blocks") or []:
            # blocks: (x0, y0, x1, y1, text, block_no, block_type)
            if len(b) < 4:
                continue
            x0, y0, x1, y1 = b[:4]
            covered += max(0.0, (x1 - x0)) * max(0.0, (y1 - y0))
        return (covered / page_area) >= min_area_frac

    @staticmethod
    def _images_from_image_file(
        path,
        max_image_dim: int,
        *,
        image_preprocessor: Optional[ImagePreprocessor] = None,
    ) -> dict[int, str]:
        """Load a JPEG/PNG/TIFF/BMP; multi-frame TIFFs become multiple pages."""
        images: dict[int, str] = {}
        with Image.open(path) as src:
            for page_num, frame in enumerate(ImageSequence.Iterator(src)):
                img = frame.convert("RGB").copy()
                if image_preprocessor is not None:
                    bgr = np.asarray(img)[:, :, ::-1].copy()  # RGB -> BGR
                    bgr = image_preprocessor(bgr, page_num=page_num)
                    images[page_num] = _bgr_to_base64_jpeg(
                        bgr, max_dim=max_image_dim, quality=80
                    )
                    continue
                img.thumbnail((max_image_dim, max_image_dim))
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=80)
                images[page_num] = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return images

    def embed_structured_text(
        self,
        input_pdf_path: str,
        output_pdf_path: str,
        pages_data: dict[int, list[tuple[list[float], str]]],
        dpi: int = 200,
    ) -> None:
        """
        Build a searchable "sandwich" PDF: rasterize each page as a background
        image and overlay invisible text positioned to match the source layout.

        Accepts either a PDF or a raw image (JPEG/PNG/TIFF/BMP/WebP) as input.
        Image inputs are converted to a 1-page-per-frame PDF — no
        rasterization-to-PDF-to-rasterization round trip required.

        Args:
            input_pdf_path: Path to the source PDF or image file.
            output_pdf_path: Where to write the searchable PDF.
            pages_data: {page_num: [([nx0, ny0, nx1, ny1], text), ...]} with
                normalized (0..1) box coordinates.
            dpi: Rasterization DPI for PDF-sourced backgrounds (ignored for
                image inputs — they're used at native resolution).
        """
        if _is_image_path(input_pdf_path):
            self._embed_from_image_input(input_pdf_path, output_pdf_path, pages_data)
            return

        doc = fitz.open(input_pdf_path)
        new_doc = fitz.open()

        try:
            for page_num in range(len(doc)):
                old_page = doc[page_num]
                width = old_page.rect.width
                height = old_page.rect.height

                pix = old_page.get_pixmap(dpi=dpi)
                img_data = pix.tobytes("jpg", jpg_quality=80)

                new_page = new_doc.new_page(width=width, height=height)
                new_page.insert_image(new_page.rect, stream=img_data)

                for rect_coords, text in pages_data.get(page_num, []):
                    self._draw_invisible_text(new_page, rect_coords, text, width, height)

            new_doc.save(output_pdf_path)
        finally:
            new_doc.close()
            doc.close()

    def _embed_from_image_input(
        self,
        image_path: str,
        output_pdf_path: str,
        pages_data: dict,
    ) -> None:
        """Build a sandwich PDF directly from an image (single- or multi-frame)."""
        new_doc = fitz.open()
        try:
            with Image.open(image_path) as src:
                for page_num, frame in enumerate(ImageSequence.Iterator(src)):
                    img = frame.convert("RGB")
                    # One PDF point = 1/72 inch. Assume image is 72 DPI so
                    # pixel count equals page size in points. Concrete value
                    # doesn't matter — all coords are normalized.
                    width, height = float(img.width), float(img.height)

                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85)
                    img_data = buf.getvalue()

                    new_page = new_doc.new_page(width=width, height=height)
                    new_page.insert_image(new_page.rect, stream=img_data)

                    for rect_coords, text in pages_data.get(page_num, []):
                        self._draw_invisible_text(
                            new_page, rect_coords, text, width, height
                        )
            new_doc.save(output_pdf_path)
        finally:
            new_doc.close()

    @staticmethod
    def _draw_invisible_text(page, rect_coords, text, page_width, page_height):
        """
        Embed invisible `text` so its glyph bboxes span the *full width* of
        the source bbox — selecting anywhere inside the bbox in a PDF viewer
        returns the text.

        Strategy: size the font by box height (glyphs never exceed the box
        vertically → no bleeding into neighbouring rows), then apply a
        horizontal-scale matrix via the `morph` parameter so rendered glyph
        bboxes span the box width. `render_mode=3` keeps the layer invisible;
        the geometric distortion only affects selection/search extents, not
        Unicode codepoints (copy, Ctrl+F, accessibility tools still return
        the original text verbatim).

        Why not `min(width_based, height_based)` fontsize like before?
        Whichever constraint is tighter wins, and when height is tighter
        (short wide boxes: headings, form labels, fields) the text ends
        partway across the box — selection on the right side returns
        nothing. Sizing to fill width instead causes vertical overflow
        that bleeds into neighbouring rows. Horizontal scaling decouples
        the two axes: height fits, width fills, neither constraint is
        violated.
        """
        text = (text or "").strip()
        if not text:
            return  # empty box — nothing to embed

        nx0, ny0, nx1, ny1 = rect_coords
        pdf_rect = fitz.Rect(
            nx0 * page_width,
            ny0 * page_height,
            nx1 * page_width,
            ny1 * page_height,
        )

        # Multi-line means this block holds the whole-page fallback text
        # (used when the aligner saw zero detected boxes).
        if "\n" in text:
            fallback_rect = fitz.Rect(10, 10, page_width - 10, page_height - 10)
            page.insert_textbox(
                fallback_rect, text,
                fontsize=6, fontname="helv",
                render_mode=3, color=(0, 0, 0), align=0,
            )
            return

        box_width = pdf_rect.width
        box_height = pdf_rect.height
        if box_width <= 0 or box_height <= 0:
            return

        font = fitz.Font("helv")

        # Size so the full glyph extent (ascender - descender in em-units)
        # fits exactly inside the box height. For Helvetica this works out
        # to ~box_height/1.374 ≈ box_height * 0.728 — tighter than the old
        # 0.85 constant, and eliminates the ascender overshoot we used to
        # tolerate at the top edge.
        ascender = getattr(font, "ascender", 1.075)  # Helvetica fallback
        descender = getattr(font, "descender", -0.299)
        extent_em = max(0.01, ascender - descender)  # descender is negative
        fontsize = max(3.0, min(72.0, box_height / extent_em))

        natural_width = font.text_length(text, fontsize=fontsize)
        if natural_width <= 0:
            return  # nothing measurable to draw (e.g. all-whitespace)

        # Horizontal scale so extracted word bbox spans the full box width
        # (minus a hairline margin so we don't butt up against neighbours).
        # scale_x > 1 stretches; scale_x < 1 compresses — both correctly
        # size the word's bounding box, which is what selection uses.
        target_width = max(1.0, box_width * 0.98)
        scale_x = target_width / natural_width

        # Place baseline at box bottom, shifted up by the descender so tails
        # of "g"/"p"/"y" sit inside the box and the glyph tops land on the
        # box top (since ascender*fontsize + |descender|*fontsize = box_height
        # by construction).
        baseline = fitz.Point(pdf_rect.x0, pdf_rect.y1 + descender * fontsize)

        # Morph pivot = baseline. Matrix scales x around that pivot so
        # the text's starting x stays at pdf_rect.x0 and the end x lands
        # at pdf_rect.x0 + target_width.
        morph = (baseline, fitz.Matrix(scale_x, 1.0))
        page.insert_text(
            baseline, text,
            fontsize=fontsize, fontname="helv",
            render_mode=3, color=(0, 0, 0),
            morph=morph,
        )
