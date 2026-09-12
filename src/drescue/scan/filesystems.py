"""Filesystem identification by superblock signature.

Two uses:

* :func:`identify_filesystem` — "what is at this offset?", used to label the
  partitions found in a partition table.
* :func:`find_lost_filesystems` — "where *were* the partitions?", a signature
  sweep that reconstructs volume starts when the partition table itself is gone
  (the job DMDE's full scan does).  The sweep is magic-string based
  (``bytes.find`` over large chunks), then every hit is confirmed by a full
  superblock parse, so false positives are rare and it runs at I/O speed.

Field offsets are taken from each filesystem's on-disk layout.  Where a field is
less certain it is parsed defensively: implausible values are dropped rather
than reported, so a wrong guess shows up as a missing label, never as a lie.
"""

from __future__ import annotations

import struct
import uuid
from dataclasses import dataclass, field
from typing import Callable, Iterator, Sequence

MiB = 1024 * 1024


@dataclass
class FilesystemInfo:
    kind: str
    offset: int = 0
    label: str = ""
    uuid: str = ""
    block_size: int = 0
    size: int = 0  # bytes, 0 when unknown
    details: dict[str, object] = field(default_factory=dict)

    def describe(self) -> str:
        bits = [self.kind]
        if self.label:
            bits.append(f"label={self.label!r}")
        if self.size:
            bits.append(f"size={self.size / MiB:.1f}MiB")
        if self.uuid:
            bits.append(f"uuid={self.uuid}")
        return " ".join(bits)


@dataclass(frozen=True)
class Probe:
    kind: str
    magic: bytes
    #: Offset of ``magic`` relative to the start of the filesystem.
    magic_offset: int
    parser: Callable[[bytes, int], FilesystemInfo | None]
    #: Bytes to read from the filesystem start for the parser.
    window: int = 4096


def _text(raw: bytes) -> str:
    s = raw.split(b"\0")[0].decode("latin-1", "replace").strip()
    return s if all(32 <= ord(c) < 127 for c in s) else ""


def _uuid_or_blank(raw: bytes) -> str:
    if len(raw) != 16 or raw == b"\0" * 16:
        return ""
    return str(uuid.UUID(bytes=raw))


# ------------------------------------------------------------------- parsers
def _parse_ntfs(buf: bytes, off: int) -> FilesystemInfo | None:
    if len(buf) < 0x50:
        return None
    bps, spc = struct.unpack_from("<HB", buf, 0x0B)
    if bps not in (256, 512, 1024, 2048, 4096) or spc == 0:
        return None
    total = struct.unpack_from("<Q", buf, 0x28)[0]
    serial = struct.unpack_from("<Q", buf, 0x48)[0]
    mft = struct.unpack_from("<Q", buf, 0x30)[0]
    return FilesystemInfo(
        kind="NTFS", offset=off, block_size=bps * spc,
        size=(total + 1) * bps,
        uuid=f"{serial:016X}",
        details={"sector_size": bps, "sectors_per_cluster": spc, "mft_cluster": mft},
    )


def _parse_exfat(buf: bytes, off: int) -> FilesystemInfo | None:
    if len(buf) < 0x78:
        return None
    volume_length = struct.unpack_from("<Q", buf, 0x48)[0]
    bps_shift, spc_shift = buf[0x6C], buf[0x6D]
    if not (9 <= bps_shift <= 12) or spc_shift > 25:
        return None
    bps = 1 << bps_shift
    serial = struct.unpack_from("<I", buf, 0x64)[0]
    return FilesystemInfo(
        kind="exFAT", offset=off, block_size=bps << spc_shift,
        size=volume_length * bps, uuid=f"{serial:08X}",
        details={"sector_size": bps},
    )


def _parse_fat(buf: bytes, off: int) -> FilesystemInfo | None:
    if len(buf) < 0x5A:
        return None
    bps, spc = struct.unpack_from("<HB", buf, 0x0B)
    if bps not in (512, 1024, 2048, 4096) or spc not in (1, 2, 4, 8, 16, 32, 64, 128):
        return None
    total16 = struct.unpack_from("<H", buf, 0x13)[0]
    total32 = struct.unpack_from("<I", buf, 0x20)[0]
    total = total16 or total32
    fat32 = buf[0x52:0x57] == b"FAT32"
    label = _text(buf[0x47:0x52] if fat32 else buf[0x2B:0x36])
    serial = struct.unpack_from("<I", buf, 0x43 if fat32 else 0x27)[0]
    kind = "FAT32" if fat32 else _text(buf[0x36:0x3E]) or "FAT"
    return FilesystemInfo(
        kind=kind, offset=off, label=label, block_size=bps * spc,
        size=total * bps, uuid=f"{serial:08X}", details={"sector_size": bps},
    )


def _parse_ext(buf: bytes, off: int) -> FilesystemInfo | None:
    sb = buf[1024:2048]
    if len(sb) < 264 or struct.unpack_from("<H", sb, 56)[0] != 0xEF53:
        return None
    blocks_lo = struct.unpack_from("<I", sb, 4)[0]
    log_bs = struct.unpack_from("<I", sb, 24)[0]
    if log_bs > 6:
        return None
    block_size = 1024 << log_bs
    compat, incompat = struct.unpack_from("<I", sb, 92)[0], struct.unpack_from("<I", sb, 96)[0]
    blocks_hi = struct.unpack_from("<I", sb, 0x150)[0] if incompat & 0x80 else 0
    blocks = blocks_lo | (blocks_hi << 32)
    if incompat & 0x40:  # INCOMPAT_EXTENTS
        kind = "ext4"
    elif compat & 0x4:  # COMPAT_HAS_JOURNAL
        kind = "ext3"
    else:
        kind = "ext2"
    return FilesystemInfo(
        kind=kind, offset=off, label=_text(sb[120:136]),
        uuid=_uuid_or_blank(sb[104:120]), block_size=block_size,
        size=blocks * block_size,
        details={"inodes": struct.unpack_from("<I", sb, 0)[0]},
    )


def _parse_xfs(buf: bytes, off: int) -> FilesystemInfo | None:
    if len(buf) < 128:
        return None
    block_size, = struct.unpack_from(">I", buf, 4)
    dblocks, = struct.unpack_from(">Q", buf, 8)
    if block_size < 512 or block_size > 65536:
        return None
    return FilesystemInfo(
        kind="XFS", offset=off, block_size=block_size, size=dblocks * block_size,
        uuid=_uuid_or_blank(buf[32:48]), label=_text(buf[108:120]),
    )


def _parse_btrfs(buf: bytes, off: int) -> FilesystemInfo | None:
    sb = buf[0x10000:0x11000]
    if len(sb) < 0x100 or sb[0x40:0x48] != b"_BHRfS_M":
        return None
    total_bytes, = struct.unpack_from("<Q", sb, 0x70)
    sector_size, = struct.unpack_from("<I", sb, 0x90)
    label = _text(sb[0x12B:0x22B]) if len(sb) >= 0x22B else ""
    return FilesystemInfo(
        kind="btrfs", offset=off, uuid=_uuid_or_blank(sb[0x20:0x30]),
        block_size=sector_size if 512 <= sector_size <= 65536 else 0,
        size=total_bytes, label=label,
    )


def _parse_hfsplus(buf: bytes, off: int) -> FilesystemInfo | None:
    vh = buf[1024:1024 + 512]
    if len(vh) < 64 or vh[:2] not in (b"H+", b"HX"):
        return None
    block_size, = struct.unpack_from(">I", vh, 40)
    total_blocks, = struct.unpack_from(">I", vh, 44)
    if block_size < 512 or block_size > 1 << 20:
        return None
    return FilesystemInfo(
        kind="HFS+" if vh[:2] == b"H+" else "HFSX", offset=off,
        block_size=block_size, size=total_blocks * block_size,
    )


def _parse_apfs(buf: bytes, off: int) -> FilesystemInfo | None:
    if len(buf) < 0x40 or buf[0x20:0x24] != b"NXSB":
        return None
    block_size, = struct.unpack_from("<I", buf, 0x24)
    block_count, = struct.unpack_from("<Q", buf, 0x28)
    if block_size not in (4096, 8192, 16384, 512):
        return None
    return FilesystemInfo(
        kind="APFS container", offset=off, block_size=block_size,
        size=block_size * block_count,
    )


def _parse_iso9660(buf: bytes, off: int) -> FilesystemInfo | None:
    pvd = buf[0x8000:0x8800]
    if len(pvd) < 0x58 or pvd[1:6] != b"CD001":
        return None
    blocks, = struct.unpack_from("<I", pvd, 80)
    block_size, = struct.unpack_from("<H", pvd, 128)
    return FilesystemInfo(
        kind="ISO9660", offset=off, label=_text(pvd[40:72]),
        block_size=block_size or 2048, size=blocks * (block_size or 2048),
    )


def _parse_swap(buf: bytes, off: int) -> FilesystemInfo | None:
    if len(buf) < 4096:
        return None
    tail = buf[4096 - 10 : 4096]
    if tail not in (b"SWAPSPACE2", b"SWAP-SPACE"):
        return None
    last_page, = struct.unpack_from("<I", buf, 1024 + 4)
    return FilesystemInfo(
        kind="Linux swap", offset=off, uuid=_uuid_or_blank(buf[1024 + 12 : 1024 + 28]),
        label=_text(buf[1024 + 28 : 1024 + 44]), block_size=4096,
        size=(last_page + 1) * 4096 if last_page < (1 << 40) else 0,
    )


def _parse_luks(buf: bytes, off: int) -> FilesystemInfo | None:
    if len(buf) < 208 or buf[:6] != b"LUKS\xba\xbe":
        return None
    version, = struct.unpack_from(">H", buf, 6)
    cipher = _text(buf[8:40])
    return FilesystemInfo(
        kind=f"LUKS{version}", offset=off, uuid=_text(buf[168:208]),
        details={"cipher": cipher},
    )


def _parse_squashfs(buf: bytes, off: int) -> FilesystemInfo | None:
    if len(buf) < 48 or buf[:4] != b"hsqs":
        return None
    total, = struct.unpack_from("<Q", buf, 40)
    return FilesystemInfo(kind="squashfs", offset=off, size=total)


def _parse_f2fs(buf: bytes, off: int) -> FilesystemInfo | None:
    sb = buf[1024:1024 + 512]
    if len(sb) < 128 or struct.unpack_from("<I", sb, 0)[0] != 0xF2F52010:
        return None
    log_blocksize, = struct.unpack_from("<I", sb, 12)
    block_size = 1 << log_blocksize if log_blocksize < 24 else 4096
    block_count, = struct.unpack_from("<Q", sb, 36)
    return FilesystemInfo(
        kind="F2FS", offset=off, block_size=block_size, size=block_count * block_size
    )


def _parse_lvm(buf: bytes, off: int) -> FilesystemInfo | None:
    for sector in range(4):
        base = sector * 512
        if buf[base : base + 8] == b"LABELONE" and buf[base + 24 : base + 32] == b"LVM2 001":
            return FilesystemInfo(
                kind="LVM2 physical volume", offset=off,
                uuid=_text(buf[base + 32 : base + 64]),
            )
    return None


#: Ordered so that more specific probes win (NTFS before FAT, etc.).
PROBES: tuple[Probe, ...] = (
    Probe("NTFS", b"NTFS    ", 0x03, _parse_ntfs, 512),
    Probe("exFAT", b"EXFAT   ", 0x03, _parse_exfat, 512),
    Probe("ext", b"\x53\xef", 1024 + 56, _parse_ext, 2048),
    Probe("XFS", b"XFSB", 0, _parse_xfs, 512),
    Probe("btrfs", b"_BHRfS_M", 0x10040, _parse_btrfs, 0x11000),
    Probe("HFS+", b"H+", 1024, _parse_hfsplus, 2048),
    Probe("HFSX", b"HX", 1024, _parse_hfsplus, 2048),
    Probe("APFS", b"NXSB", 0x20, _parse_apfs, 512),
    Probe("ISO9660", b"CD001", 0x8001, _parse_iso9660, 0x8800),
    Probe("Linux swap", b"SWAPSPACE2", 4096 - 10, _parse_swap, 4096),
    Probe("Linux swap", b"SWAP-SPACE", 4096 - 10, _parse_swap, 4096),
    Probe("LUKS", b"LUKS\xba\xbe", 0, _parse_luks, 512),
    Probe("squashfs", b"hsqs", 0, _parse_squashfs, 512),
    Probe("F2FS", b"\x10\x20\xf5\xf2", 1024, _parse_f2fs, 2048),
    Probe("LVM2", b"LABELONE", 512, _parse_lvm, 2048),
    Probe("FAT32", b"FAT32   ", 0x52, _parse_fat, 512),
    Probe("FAT16", b"FAT16   ", 0x36, _parse_fat, 512),
    Probe("FAT12", b"FAT12   ", 0x36, _parse_fat, 512),
    Probe("FAT", b"FAT     ", 0x36, _parse_fat, 512),
)

_MAX_WINDOW = max(p.window for p in PROBES)


def identify_filesystem(reader, offset: int = 0, probes: Sequence[Probe] = PROBES) -> FilesystemInfo | None:
    """Identify the filesystem starting at ``offset`` (returns ``None`` if unknown)."""
    try:
        buf = reader.pread(offset, _MAX_WINDOW)
    except OSError:
        return None
    if not buf:
        return None
    return _identify_buffer(buf, offset, probes)


def _identify_buffer(buf: bytes, offset: int, probes: Sequence[Probe] = PROBES) -> FilesystemInfo | None:
    for probe in probes:
        end = probe.magic_offset + len(probe.magic)
        if len(buf) < end or buf[probe.magic_offset : end] != probe.magic:
            continue
        info = probe.parser(buf, offset)
        if info is not None:
            return info
    return None


def find_lost_filesystems(
    reader,
    start: int = 0,
    end: int | None = None,
    *,
    sector_size: int = 512,
    chunk_size: int = 8 * MiB,
    known: Sequence[tuple[int, int]] = (),
    on_progress: Callable[[int, int], None] | None = None,
) -> Iterator[FilesystemInfo]:
    """Sweep the medium for filesystem superblocks and yield confirmed hits.

    ``known`` is a list of ``(start, size)`` ranges already accounted for by a
    partition table; hits inside them are suppressed so the output is exactly
    the *lost* volumes.
    """
    end = end if end is not None else getattr(reader, "size", 0)
    max_back = max(p.magic_offset for p in PROBES)
    pos = start
    seen: set[int] = set()
    while pos < end:
        want = min(chunk_size, end - pos)
        try:
            chunk = reader.pread(pos, want)
        except OSError:
            pos += want
            continue
        if not chunk:
            break
        for probe in PROBES:
            idx = chunk.find(probe.magic)
            while idx != -1:
                fs_start = pos + idx - probe.magic_offset
                if (
                    fs_start >= 0
                    and fs_start % sector_size == 0
                    and fs_start not in seen
                    and not _inside(fs_start, known)
                ):
                    info = identify_filesystem(reader, fs_start, (probe,))
                    if info is not None:
                        seen.add(fs_start)
                        yield info
                idx = chunk.find(probe.magic, idx + 1)
        if on_progress is not None:
            on_progress(pos + len(chunk) - start, end - start)
        # Overlap so a magic straddling the chunk boundary is not missed.
        pos += max(len(chunk) - max_back, sector_size)


def _inside(pos: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(p <= pos < p + s for p, s in ranges)
