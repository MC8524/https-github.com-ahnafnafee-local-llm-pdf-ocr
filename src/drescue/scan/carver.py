"""Signature-based file carving, aware of which sectors were actually rescued.

Ordinary carvers (PhotoRec and friends) treat an image as trustworthy bytes.
After a rescue that is false: the holes the drive refused to give up are zeros
in the image and look like perfectly good file content.  This carver takes the
mapfile produced by :mod:`drescue.rescue` and reports, per extracted file, how
many bytes came from unreadable areas — so a photo that is 3 % hole is flagged
instead of silently shipped as recovered.

Where a format allows it the exact file length is computed from its own headers
(PNG chunk walk, JPEG marker walk, RIFF/BMP/SQLite/ELF size fields, MP4 box
walk, ZIP end-of-central-directory); otherwise the carve stops at a footer or at
``max_size``.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass, field
from typing import Callable, Iterator, Sequence

from ..extents import FINISHED, ExtentMap, Range

KiB, MiB = 1024, 1024 * 1024

LengthFn = Callable[["_Window", int], int | None]


@dataclass(frozen=True)
class Signature:
    name: str
    ext: str
    header: bytes
    max_size: int = 64 * MiB
    min_size: int = 0
    footer: bytes | None = None
    footer_include: bool = True
    length_fn: LengthFn | None = None
    #: Swallow the CR/LF that usually follows a textual footer (PDF, RTF).
    trailing_eol: bool = False
    #: Refine the extension from the first bytes of the carved file.
    refine: Callable[[bytes], str | None] | None = None


@dataclass
class CarvedFile:
    offset: int
    size: int
    ext: str
    name: str
    path: str = ""
    hole_bytes: int = 0
    read_errors: int = 0
    holes: list[Range] = field(default_factory=list)

    @property
    def suspect(self) -> bool:
        return self.hole_bytes > 0 or self.read_errors > 0

    @property
    def integrity(self) -> float:
        return 0.0 if not self.size else 1.0 - self.hole_bytes / self.size


class _Window:
    """Cached sequential reader used by the length functions."""

    def __init__(self, reader, start: int, limit: int) -> None:
        self.reader = reader
        self.start = start
        self.limit = limit
        self._cache: dict[int, bytes] = {}
        self._block = 64 * KiB

    def read(self, offset: int, size: int) -> bytes:
        """Read ``size`` bytes at ``offset`` *relative to the file start*."""
        if offset < 0 or size <= 0 or offset >= self.limit:
            return b""
        size = min(size, self.limit - offset)
        out = bytearray()
        pos = offset
        while len(out) < size:
            blk = pos // self._block
            buf = self._cache.get(blk)
            if buf is None:
                try:
                    buf = self.reader.pread(self.start + blk * self._block, self._block)
                except OSError:
                    buf = b""
                self._cache[blk] = buf
            off = pos - blk * self._block
            piece = buf[off : off + (size - len(out))]
            if not piece:
                break
            out += piece
            pos += len(piece)
        return bytes(out)


# ------------------------------------------------------------- length helpers
def _len_png(w: _Window, _max: int) -> int | None:
    pos = 8
    while pos + 8 <= w.limit:
        head = w.read(pos, 8)
        if len(head) < 8:
            return None
        size, ctype = struct.unpack(">I", head[:4])[0], head[4:8]
        if size > 0x7FFFFFFF:
            return None
        pos += 12 + size
        if ctype == b"IEND":
            return pos
    return None


def _len_jpeg(w: _Window, _max: int) -> int | None:
    pos = 2
    while pos + 4 <= w.limit:
        head = w.read(pos, 4)
        if len(head) < 4 or head[0] != 0xFF:
            return None
        marker = head[1]
        if marker == 0xD9:
            return pos + 2
        if 0xD0 <= marker <= 0xD8 or marker == 0x01:
            pos += 2
            continue
        seg = struct.unpack(">H", head[2:4])[0]
        if seg < 2:
            return None
        pos += 2 + seg
        if marker == 0xDA:  # start of scan: entropy-coded data until EOI
            return _scan_to_eoi(w, pos)
    return None


def _scan_to_eoi(w: _Window, pos: int) -> int | None:
    while pos < w.limit:
        buf = w.read(pos, 256 * KiB)
        if not buf:
            return None
        i = 0
        while True:
            i = buf.find(b"\xff", i)
            if i == -1 or i + 1 >= len(buf):
                break
            nxt = buf[i + 1]
            if nxt == 0xD9:
                return pos + i + 2
            if nxt == 0x00 or 0xD0 <= nxt <= 0xD7:
                i += 2
                continue
            i += 1
        pos += max(len(buf) - 1, 1)
    return None


def _len_gif(w: _Window, _max: int) -> int | None:
    head = w.read(0, 13)
    if len(head) < 13:
        return None
    flags = head[10]
    pos = 13 + (3 << ((flags & 7) + 1) if flags & 0x80 else 0)
    while pos < w.limit:
        b = w.read(pos, 1)
        if not b:
            return None
        if b[0] == 0x3B:
            return pos + 1
        if b[0] == 0x21:  # extension block
            pos += 2
        elif b[0] == 0x2C:  # image descriptor
            desc = w.read(pos, 10)
            if len(desc) < 10:
                return None
            local = desc[9]
            pos += 10 + (3 << ((local & 7) + 1) if local & 0x80 else 0) + 1
        else:
            return None
        pos = _skip_sub_blocks(w, pos)
        if pos is None:
            return None
    return None


def _skip_sub_blocks(w: _Window, pos: int) -> int | None:
    while pos < w.limit:
        b = w.read(pos, 1)
        if not b:
            return None
        if b[0] == 0:
            return pos + 1
        pos += 1 + b[0]
    return None


def _len_riff(w: _Window, _max: int) -> int | None:
    head = w.read(0, 8)
    if len(head) < 8:
        return None
    return struct.unpack("<I", head[4:8])[0] + 8


def _len_bmp(w: _Window, _max: int) -> int | None:
    head = w.read(0, 6)
    if len(head) < 6:
        return None
    size = struct.unpack("<I", head[2:6])[0]
    return size if size >= 54 else None


def _len_sqlite(w: _Window, _max: int) -> int | None:
    head = w.read(0, 32)
    if len(head) < 32:
        return None
    page_size = struct.unpack(">H", head[16:18])[0]
    page_size = 65536 if page_size == 1 else page_size
    pages = struct.unpack(">I", head[28:32])[0]
    if page_size < 512 or page_size & (page_size - 1) or not pages:
        return None
    return page_size * pages


def _len_zip(w: _Window, max_size: int) -> int | None:
    pos = 0
    while pos < min(w.limit, max_size):
        buf = w.read(pos, 1 * MiB)
        if not buf:
            return None
        i = buf.find(b"PK\x05\x06")
        if i != -1 and len(buf) >= i + 22:
            comment = struct.unpack("<H", buf[i + 20 : i + 22])[0]
            return pos + i + 22 + comment
        pos += max(len(buf) - 21, 1)
    return None


def _len_mp4(w: _Window, max_size: int) -> int | None:
    pos = 0
    while pos < min(w.limit, max_size):
        head = w.read(pos, 16)
        if len(head) < 8:
            break
        size = struct.unpack(">I", head[:4])[0]
        btype = head[4:8]
        if not all(0x20 <= c < 0x7F for c in btype):
            break
        if size == 1:
            if len(head) < 16:
                break
            size = struct.unpack(">Q", head[8:16])[0]
        elif size == 0:
            return w.limit
        if size < 8:
            break
        pos += size
    return pos if pos > 8 else None


def _len_elf(w: _Window, _max: int) -> int | None:
    head = w.read(0, 64)
    if len(head) < 52:
        return None
    is64 = head[4] == 2
    little = head[5] == 1
    e = "<" if little else ">"
    if is64:
        if len(head) < 64:
            return None
        shoff = struct.unpack_from(e + "Q", head, 0x28)[0]
        shentsize, shnum = struct.unpack_from(e + "HH", head, 0x3A)
    else:
        shoff = struct.unpack_from(e + "I", head, 0x20)[0]
        shentsize, shnum = struct.unpack_from(e + "HH", head, 0x2E)
    end = shoff + shentsize * shnum
    return end if end > 0 else None


def _refine_zip(head: bytes) -> str | None:
    probe = head[:8 * KiB]
    if b"word/" in probe:
        return "docx"
    if b"xl/" in probe:
        return "xlsx"
    if b"ppt/" in probe:
        return "pptx"
    if b"mimetypeapplication/epub+zip" in probe.replace(b"\x00", b""):
        return "epub"
    if b"META-INF/MANIFEST.MF" in probe:
        return "jar"
    return None


SIGNATURES: tuple[Signature, ...] = (
    Signature("JPEG", "jpg", b"\xff\xd8\xff", length_fn=_len_jpeg, footer=b"\xff\xd9", min_size=128),
    Signature("PNG", "png", b"\x89PNG\r\n\x1a\n", length_fn=_len_png, footer=b"IEND\xaeB`\x82"),
    Signature("GIF", "gif", b"GIF8", length_fn=_len_gif, footer=b"\x00\x3b"),
    Signature("PDF", "pdf", b"%PDF-", footer=b"%%EOF", trailing_eol=True, max_size=256 * MiB),
    Signature("ZIP", "zip", b"PK\x03\x04", length_fn=_len_zip, refine=_refine_zip, max_size=512 * MiB),
    Signature("RIFF", "riff", b"RIFF", length_fn=_len_riff,
              refine=lambda h: {b"WAVE": "wav", b"AVI ": "avi", b"WEBP": "webp"}.get(h[8:12])),
    Signature("BMP", "bmp", b"BM", length_fn=_len_bmp, min_size=54),
    Signature("SQLite", "sqlite", b"SQLite format 3\x00", length_fn=_len_sqlite),
    Signature("MP4/MOV", "mp4", b"\x00\x00\x00\x18ftyp", length_fn=_len_mp4, max_size=4096 * MiB),
    Signature("MP4/MOV", "mp4", b"\x00\x00\x00\x20ftyp", length_fn=_len_mp4, max_size=4096 * MiB),
    Signature("ELF", "elf", b"\x7fELF", length_fn=_len_elf),
    Signature("OLE2 (doc/xls/ppt)", "ole", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", max_size=128 * MiB),
    Signature("GZIP", "gz", b"\x1f\x8b\x08"),
    Signature("BZIP2", "bz2", b"BZh"),
    Signature("XZ", "xz", b"\xfd7zXZ\x00"),
    Signature("7-Zip", "7z", b"7z\xbc\xaf\x27\x1c", max_size=512 * MiB),
    Signature("RAR", "rar", b"Rar!\x1a\x07", max_size=512 * MiB),
    Signature("TIFF", "tif", b"II*\x00"),
    Signature("TIFF", "tif", b"MM\x00*"),
    Signature("MP3", "mp3", b"ID3", max_size=32 * MiB),
    Signature("FLAC", "flac", b"fLaC", max_size=512 * MiB),
    Signature("Ogg", "ogg", b"OggS", max_size=512 * MiB),
    Signature("Matroska/WebM", "mkv", b"\x1aE\xdf\xa3", max_size=4096 * MiB),
    Signature("RTF", "rtf", b"{\\rtf", footer=b"}", trailing_eol=True, max_size=32 * MiB),
    Signature("SQLite WAL", "wal", b"\x37\x7f\x06\x82", max_size=64 * MiB),
)

_MAX_HEADER = max(len(s.header) for s in SIGNATURES)


@dataclass
class CarveConfig:
    #: Candidate headers must sit on a multiple of this (cluster/sector size).
    alignment: int = 512
    chunk_size: int = 8 * MiB
    #: Skip headers found inside an already-carved file (avoids JPEGs in PDFs).
    skip_nested: bool = True
    #: Do not write files whose data overlaps unrescued sectors.
    skip_suspect: bool = False
    max_files: int | None = None
    signatures: Sequence[Signature] = SIGNATURES
    extensions: Sequence[str] | None = None  # restrict to these extensions


def carve(
    reader,
    outdir: str | os.PathLike[str] | None,
    *,
    config: CarveConfig | None = None,
    rescued: ExtentMap | None = None,
    start: int = 0,
    end: int | None = None,
    on_progress: Callable[[int, int, int], None] | None = None,
) -> Iterator[CarvedFile]:
    """Carve files out of ``reader`` into ``outdir`` (dry run when ``outdir`` is None).

    ``rescued`` is the rescue mapfile's extent map; when supplied, every carved
    file records the bytes that came from areas never successfully read.
    """
    cfg = config or CarveConfig()
    sigs = [
        s for s in cfg.signatures
        if cfg.extensions is None or s.ext in cfg.extensions
    ]
    end = end if end is not None else getattr(reader, "size", 0)
    pos = start
    carved = 0
    skip_until = start
    while pos < end:
        try:
            chunk = reader.pread(pos, min(cfg.chunk_size, end - pos))
        except OSError:
            pos += cfg.chunk_size
            continue
        if not chunk:
            break
        hits: list[tuple[int, Signature]] = []
        for sig in sigs:
            idx = chunk.find(sig.header)
            while idx != -1:
                abs_pos = pos + idx
                if abs_pos % cfg.alignment == 0:
                    hits.append((abs_pos, sig))
                idx = chunk.find(sig.header, idx + 1)
        hits.sort(key=lambda h: h[0])
        for abs_pos, sig in hits:
            if cfg.skip_nested and abs_pos < skip_until:
                continue
            size = _measure(reader, abs_pos, sig, end)
            if size is None or size < max(sig.min_size, 1):
                continue
            item = _extract(reader, abs_pos, size, sig, outdir, rescued, cfg)
            if item is None:
                continue
            carved += 1
            skip_until = abs_pos + size
            yield item
            if cfg.max_files is not None and carved >= cfg.max_files:
                return
        if on_progress is not None:
            on_progress(pos + len(chunk) - start, end - start, carved)
        pos += max(len(chunk) - _MAX_HEADER, cfg.alignment)


def _measure(reader, pos: int, sig: Signature, end: int) -> int | None:
    limit = min(sig.max_size, end - pos)
    if limit <= 0:
        return None
    window = _Window(reader, pos, limit)
    if sig.length_fn is not None:
        try:
            size = sig.length_fn(window, limit)
        except (OSError, struct.error):
            size = None
        if size and 0 < size <= limit:
            return size
    if sig.footer:
        size = _find_footer(window, sig, limit)
        if size:
            if sig.trailing_eol:
                while size < limit and window.read(size, 1) in (b"\r", b"\n"):
                    size += 1
            return size
    return limit


def _find_footer(window: _Window, sig: Signature, limit: int) -> int | None:
    """Last occurrence of the footer within the window (handles trailing data)."""
    assert sig.footer is not None
    best = None
    pos = 0
    step = 1 * MiB
    while pos < limit:
        buf = window.read(pos, step)
        if not buf:
            break
        i = buf.rfind(sig.footer)
        if i != -1:
            best = pos + i + (len(sig.footer) if sig.footer_include else 0)
        pos += max(len(buf) - len(sig.footer), 1)
    return best


def _extract(reader, pos: int, size: int, sig: Signature, outdir, rescued, cfg) -> CarvedFile | None:
    holes = _holes(rescued, pos, size)
    hole_bytes = sum(s for _, s in holes)
    if cfg.skip_suspect and hole_bytes:
        return None
    ext = sig.ext
    head = _safe(reader, pos, min(8 * KiB, size))
    if sig.refine is not None:
        ext = sig.refine(head) or ext
    name = f"f{pos:016x}.{ext}"
    item = CarvedFile(offset=pos, size=size, ext=ext, name=name,
                      hole_bytes=hole_bytes, holes=holes)
    if outdir is None:
        return item
    target_dir = os.path.join(os.fspath(outdir), ext)
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, name)
    written = 0
    with open(path, "wb") as fh:
        while written < size:
            want = min(1 * MiB, size - written)
            try:
                data = reader.pread(pos + written, want)
            except OSError:
                # Keep file offsets intact: a hole becomes zeros, flagged below.
                data = b"\0" * want
                item.read_errors += 1
            if not data:
                break
            fh.write(data)
            written += len(data)
    item.size = written
    item.path = path
    return item


def _holes(rescued: ExtentMap | None, pos: int, size: int) -> list[Range]:
    if rescued is None:
        return []
    good = list(rescued.ranges(FINISHED, domain=[(pos, size)]))
    holes: list[Range] = []
    cursor = pos
    for gpos, gsize in sorted(good):
        if gpos > cursor:
            holes.append((cursor, gpos - cursor))
        cursor = max(cursor, gpos + gsize)
    if cursor < pos + size:
        holes.append((cursor, pos + size - cursor))
    return holes


def _safe(reader, pos: int, size: int) -> bytes:
    try:
        return reader.pread(pos, size)
    except OSError:
        return b""
