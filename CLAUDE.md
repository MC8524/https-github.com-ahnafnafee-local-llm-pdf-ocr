# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependencies are managed with [`uv`](https://github.com/astral-sh/uv).

```bash
uv sync                                                       # install/sync deps
uv run main.py input.pdf [output.pdf]                         # CLI OCR (DP align + crop-refine)
uv run main.py input.pdf --pages 1-3,5 --dpi 300              # page range + DPI
uv run main.py input.pdf --concurrency 3                      # parallel LLM calls
uv run main.py input.pdf --no-refine                          # skip crop re-OCR (faster, less robust)
uv run main.py input.pdf --max-image-dim 640                  # smaller VLM context (needed for GLM-OCR:1.1B)
uv run main.py input.pdf --api-base http://localhost:11434/v1 --model glm-ocr:latest --max-image-dim 640   # Ollama + GLM-OCR
uv run main.py input.pdf --grounded --model qwen/qwen3-vl-8b  # grounded path: bbox-native VLM, no Surya
uv run main.py input.pdf -v                                   # verbose debug logging
uv run uvicorn server:app --reload --port 8000                # web UI at http://localhost:8000
```

This repository also contains a second, unrelated tool — `drescue`, a data
recovery utility (see `docs/DRESCUE.md`). It shares nothing with the OCR
pipeline and has no third-party dependencies:

```bash
python drescue_cli.py rescue /dev/sdb disk.img disk.map --direct   # image a failing disk
python drescue_cli.py status disk.map                              # what was recovered
python drescue_cli.py scan disk.img --deep                         # partitions + filesystems
python drescue_cli.py carve disk.img -o out -m disk.map            # recover files, flag damaged ones
uv run pytest tests/drescue -q                                     # its tests (~7s, no models)
```

Debug/inspection tools live in `scripts/` (`visualize_bboxes.py`, `debug_alignment.py`, `verify_output.py`, `inspect_pdf.py`, etc.) and are run with `uv run scripts/<name>.py <args>`.

### Tests

```bash
uv run pytest                     # full suite (~45s, loads Surya once)
uv run pytest -m "not slow"       # fast tests only, no model load (~2s)
uv run pytest -m slow             # integration: real Surya + example PDFs
uv run pytest tests/test_aligner.py -v   # single file
```

Tests live under `tests/`. `pytest-asyncio` is in auto mode so `async def test_...` works without decorators. Markers: `slow` (loads Surya), `live_llm` (hits a real LLM endpoint — not wired yet). Integration tests use the on-disk `examples/*.pdf` with a stubbed LLM to validate the full detect→align→embed path end-to-end.

### Confidence evaluation

`scripts/confidence_eval.py` scores either pipeline path against the ground-truth fixtures in `tests/fixtures/ground_truth_*.json`. Requires a live LLM; reports per-document block recall, average IoU of matched pairs, and average text similarity against the GT content.

```bash
uv run scripts/confidence_eval.py --path grounded --grounded-model qwen/qwen3-vl-8b
uv run scripts/confidence_eval.py --path hybrid --hybrid-model allenai/olmocr-2-7b
uv run scripts/confidence_eval.py --path both    # both, side by side
```

Fixture axis-order is auto-detected (`src/pdf_ocr/evaluation.py::_detect_bbox_axis_order`) since `handwritten.pdf`'s fixture uses `[x0,y0,x1,y1]` while `hybrid.pdf` and `digital.pdf` fixtures use `[y0,x0,y1,x1]`. Normalization uses each fixture's declared page dimensions.

## Configuration

LLM endpoint is read from `.env` (or CLI overrides `--api-base` / `--model`). LM Studio must be running locally and serving the vision model.

```
LLM_API_BASE=http://localhost:1234/v1
LLM_MODEL=allenai/olmocr-2-7b
OCR_CONCURRENCY=3          # server.py — async LLM concurrency
```

## Architecture

Hybrid pipeline: **Surya** does fast layout *detection only* (no recognition), a **local vision LLM** (OlmOCR via LM Studio) produces text content, and a **Needleman-Wunsch DP** binds LLM lines to detected boxes. Boxes the DP cannot confidently populate are re-OCR'd individually via per-box image crops. PyMuPDF writes a "sandwich" PDF (rasterized page image + invisible selectable text).

```
PDF → images → Surya batch detection (boxes)  ┐
            → LLM async OCR (lines)           ┴→ DP line→box alignment → crop re-OCR for gaps → output_writer → searchable PDF
```

### Alignment algorithm (`HybridAligner.align_text`)

Both sequences (LLM lines, Surya boxes) arrive in reading order, so alignment is a **monotonic** Needleman-Wunsch DP over `(N lines, M boxes)`:

- **Match cost**: relative character-count mismatch between the LLM line's length and each box's estimated capacity. Capacity is proportional to box area (width × height in normalized space), with total capacity scaled to total LLM chars — so what matters is each box's *share* of the page's text.
- **Skip ops**: `skip_line` (line unmatched; attached to the nearest matched box to preserve searchability) and `skip_box` (box left empty; cheap — many detected boxes are rules/decorations).
- **Output**: one `(box, text)` tuple per input box, in input order. Empty strings flag boxes the DP could not match — those are the refine-stage candidates.

### Refine stage (per-box crop re-OCR)

After DP, any empty box passing `_is_refinable` (~40pt × 6pt at 200 DPI) is cropped from the page image, upscaled to ≥256 px, and sent to the LLM with a minimal "transcribe only this text" prompt. This catches tables, complex multi-column layouts, and figure captions that the full-page LLM call happens to miss while staying cheap on clean prose (where most boxes have text). Disable with `--no-refine` on the CLI.

### OlmOCR prompt / YAML parsing

`OCRProcessor.perform_ocr` uses the canonical `build_no_anchoring_v4_yaml_prompt()` string from `olmocr.prompts` (the model is RL-trained on that exact prompt). Responses are markdown with YAML front matter (`primary_language`, `is_rotation_valid`, ...); `_strip_yaml_front_matter` removes the front matter before returning the body. `perform_ocr_on_crop` uses a distinct minimal prompt since per-region metadata is nonsensical.

### The orchestration seam: `src/pdf_ocr/pipeline.py`

`OCRPipeline` is the single shared driver used by both `main.py` and `server.py`. Two execution paths:

- **Hybrid** (default): `convert → detect → ocr → refine → embed` — Surya gives boxes, LLM transcribes whole page, DP binds lines to boxes, crop re-OCR fills gaps.
- **Grounded** (`grounded_backend=...`): `grounded → embed` — a bbox-native VLM (Qwen2.5-VL, Qwen3-VL, etc.) returns `(bbox, text)` pairs directly. Skips Surya, DP, and refine entirely. `src/pdf_ocr/core/grounded.py::PromptedGroundedOCR` is the default implementation; it rasterizes pages, calls the VLM with `DEFAULT_GROUNDING_PROMPT`, parses the JSON, normalizes pixel bboxes to 0..1.

Both paths take the same **injected components** so extensions can swap any phase without touching the CLI or web handlers:

| Parameter       | Contract                                                               | Default                               |
|-----------------|------------------------------------------------------------------------|---------------------------------------|
| `aligner`       | `get_detected_boxes_batch(list[bytes])` + `align_text(structured, text)` | `HybridAligner` (Surya-only)          |
| `ocr_processor` | async `perform_ocr(image_base64) -> list[str]`                         | `OCRProcessor` (OpenAI-compat LLM)    |
| `pdf_handler`   | `convert_to_images(path, dpi) -> dict[int, b64]`                       | `PDFHandler`                          |
| `output_writer` | `callable(input_path, output_path, pages_data, dpi) -> None`           | `pdf_handler.embed_structured_text`   |

`OCRPipeline.run(...)` is async, uses `asyncio.as_completed` + a `Semaphore(concurrency)` for per-page LLM work (so `concurrency=1` is the degenerate sequential case), and drives an optional progress callback:

```python
async def progress(stage: str, current: int, total: int, message: str) -> None
# stages: "convert" | "detect" | "ocr" | "embed"
```

`main.py` maps this callback onto Rich progress tasks; `server.py` maps it onto WebSocket percent updates via `_STAGE_WEIGHTS`.

### Core classes (`src/pdf_ocr/core/`)

| Class           | File        | Role                                                                          |
|-----------------|-------------|-------------------------------------------------------------------------------|
| `PDFHandler`    | `pdf.py`    | PDF↔image conversion; builds a fresh `new_doc` and overlays invisible text with `render_mode=3`. `_draw_invisible_text` auto-sizes font per box. |
| `OCRProcessor`  | `ocr.py`    | `AsyncOpenAI` client against the local LLM; `perform_ocr` returns a list of lines. |
| `HybridAligner` | `aligner.py`| Wraps Surya's `DetectionPredictor`; `get_detected_boxes_batch` runs detection on all pages in one call; `align_text` distributes LLM tokens across boxes proportionally to box width. |

### Coordinate and text conventions
- Bounding boxes are normalized `[nx0, ny0, nx1, ny1]` in `0..1` and only scaled to PDF points inside `embed_structured_text`. Don't scale them anywhere else.
- Boxes are sorted top-to-bottom, left-to-right before alignment — the aligner relies on this reading order.
- If `align_text` receives zero detected boxes, it falls back to a single full-page box containing all LLM text so search still works.
- In `embed_structured_text`, multi-line text in a box is treated as a full-page fallback block; single-line text is placed with `insert_text(point, render_mode=3)` (PyMuPDF maintainer-recommended for invisible OCR layers — `insert_textbox` mis-sizes single-line glyphs).

### Surya progress-bar silencing
`src/pdf_ocr/utils/tqdm_patch.py` is applied at the top of `aligner.py` (`tqdm_patch.apply()`) to stop Surya's internal tqdm bars from colliding with Rich. Do not remove this import — it must run before `from surya.detection import DetectionPredictor`. `main.py` also sets `TQDM_DISABLE=1` via `os.environ.setdefault` before the lazy import path loads Surya.

### Entry points

- **`main.py`** — argparse + lazy imports of heavy modules (Surya, PyMuPDF) so `--help` stays fast; wires a Rich progress adapter into `OCRPipeline`.
- **`server.py`** — FastAPI with `POST /process`, `GET /text/{job_id}`, `WS /ws/{client_id}`. The WebSocket is for live progress; the pipeline callback is translated to a single 0-100 percent via `_STAGE_WEIGHTS`.

### Extension points

Common forks / extensions map cleanly onto the injection points above:

- **Alternative layout model** (e.g. DETR): implement an aligner exposing `get_detected_boxes_batch` + `align_text` and pass it to `OCRPipeline`.
- **Alternative output format** (e.g. EPUB): write a function `writer(input_path, output_path, pages_data, dpi)` and pass it as `output_writer=`.
- **Different OCR backend**: implement `perform_ocr(image_base64) -> list[str]` and pass as `ocr_processor=`.

No entry-point edits required in any of these cases.

## `drescue` — data recovery (`src/drescue/`)

Unrelated to the OCR pipeline; it lives here only because both tools share the
repository. Standard library only — no third-party imports — because it has to
run from a rescue USB stick. Full documentation in `docs/DRESCUE.md`.

```
PDF-OCR pipeline  ── src/pdf_ocr/   (Surya + LLM, heavy deps)
drescue           ── src/drescue/   (stdlib only, entry point drescue_cli.py)
```

### What it does

Five commands: `rescue` (fault-tolerant imaging), `status` (read a mapfile),
`scan` (partitions + filesystems), `carve` (signature file recovery), `verify`
(compare image against the medium).

### Core invariants

- **The mapfile is GNU ddrescue's format, byte for byte.** Status characters are
  `?` non-tried, `*` non-trimmed, `/` non-scraped, `-` bad-sector, `+` finished.
  Mapfiles are interchangeable in both directions with `ddrescue` itself; a
  verbatim ddrescue 1.27 mapfile is parsed as a regression test. Do not
  "improve" the format.
- **`ExtentMap` is always contiguous, gap-free and merged.** Every phase is
  expressed as "read the ranges with status X, rewrite them as Y". `set_status`
  splits and re-merges; the constructor rejects a non-contiguous map.
- **Phase order is the whole point**: copy (skip fast on error) → trim (edges of
  each failed cluster) → scrape (sector by sector) → retry (bad sectors only).
  A dying drive has a limited number of reads left; the order spends them on the
  recoverable data first. Changing it changes the tool's value.
- **The source is never written to.** Opened `O_RDONLY`; destinations that are
  block devices need `--force`.
- **Bounding boxes of damage are sector-granular.** One bad sector must cost one
  sector, not one 64 KiB cluster — that is what trim and scrape buy, and there
  is a test asserting it.

### Injection seams

`Rescuer(reader, writer, mapfile, config)` takes any object with
`pread(pos, size) -> bytes` / `size` / `sector_size` as the reader and anything
with `pwrite(pos, data)` as the writer, which is how the engine is tested
against simulated bad sectors (`tests/drescue/fakes.py::FaultyReader`) instead
of a real dying disk. Adding a filesystem probe means appending a `Probe` to
`scan/filesystems.py::PROBES`; adding a carve target means appending a
`Signature` to `scan/carver.py::SIGNATURES`.

### Field parsing discipline

Filesystem and partition parsers must drop implausible values rather than report
them, so an offset that turns out to be wrong shows up as a missing label, never
as a confidently wrong one. ext2/3/4 and FAT32 are cross-validated against
`blkid` in the tests, MBR/GPT against `partx`; the other filesystems are tested
against fixtures built from the same layout assumptions as the parser, which is
a consistency check, not an independent one. `docs/DRESCUE.md` says so
explicitly — keep that disclosure accurate if you extend the probes.
