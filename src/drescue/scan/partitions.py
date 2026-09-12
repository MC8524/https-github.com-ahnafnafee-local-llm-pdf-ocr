"""MBR and GPT partition table parsing, with CRC validation and backup fallback.

Damaged disks routinely have a shredded primary GPT and an intact backup at the
far end of the medium, so the GPT reader validates CRC32s and says which copy it
used.  All offsets returned are *byte* offsets from the start of the device.
"""

from __future__ import annotations

import struct
import uuid
import zlib
from dataclasses import dataclass, field

GPT_SIGNATURE = b"EFI PART"
MBR_SIGNATURE = b"\x55\xaa"
PROTECTIVE_MBR_TYPE = 0xEE
EXTENDED_TYPES = frozenset({0x05, 0x0F, 0x85, 0xC5, 0xD5})

MBR_TYPE_NAMES = {
    0x00: "empty", 0x01: "FAT12", 0x04: "FAT16 <32M", 0x05: "extended",
    0x06: "FAT16", 0x07: "NTFS/exFAT/HPFS", 0x0B: "FAT32 CHS", 0x0C: "FAT32 LBA",
    0x0E: "FAT16 LBA", 0x0F: "extended LBA", 0x11: "hidden FAT12",
    0x27: "Windows RE", 0x42: "Windows dynamic", 0x82: "Linux swap",
    0x83: "Linux", 0x85: "Linux extended", 0x86: "NTFS volume set",
    0x8E: "Linux LVM", 0xA5: "FreeBSD", 0xA6: "OpenBSD", 0xA8: "Apple UFS",
    0xAF: "Apple HFS/HFS+", 0xEE: "GPT protective", 0xEF: "EFI system",
    0xFD: "Linux RAID auto",
}

GPT_TYPE_NAMES = {
    "c12a7328-f81f-11d2-ba4b-00a0c93ec93b": "EFI system",
    "e3c9e316-0b5c-4db8-817d-f92df00215ae": "Microsoft reserved",
    "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7": "Microsoft basic data",
    "de94bba4-06d1-4d40-a16a-bfd50179d6ac": "Windows recovery",
    "0fc63daf-8483-4772-8e79-3d69d8477de4": "Linux filesystem",
    "0657fd6d-a4ab-43c4-84e5-0933c84b4f4f": "Linux swap",
    "e6d6d379-f507-44c2-a23c-238f2a3df928": "Linux LVM",
    "a19d880f-05fc-4d3b-a006-743f0f84911e": "Linux RAID",
    "933ac7e1-2eb4-4f13-b844-0e14e2aef915": "Linux /home",
    "48465300-0000-11aa-aa11-00306543ecac": "Apple HFS+",
    "7c3457ef-0000-11aa-aa11-00306543ecac": "Apple APFS",
    "426f6f74-0000-11aa-aa11-00306543ecac": "Apple boot",
    "516e7cb4-6ecf-11d6-8ff8-00022d09712b": "FreeBSD data",
    "21686148-6449-6e6f-744e-656564454649": "BIOS boot",
}


@dataclass
class Partition:
    index: int
    start: int  # byte offset
    size: int  # bytes
    kind: str  # human-readable type
    scheme: str  # "mbr" | "gpt" | "ebr"
    name: str = ""
    type_id: str = ""
    guid: str = ""
    bootable: bool = False
    filesystem: object | None = None  # filled in by the scan command

    @property
    def end(self) -> int:
        return self.start + self.size


@dataclass
class PartitionTable:
    scheme: str  # "mbr" | "gpt" | "none"
    partitions: list[Partition] = field(default_factory=list)
    sector_size: int = 512
    disk_guid: str = ""
    notes: list[str] = field(default_factory=list)

    def __iter__(self):
        return iter(self.partitions)

    def __len__(self) -> int:
        return len(self.partitions)


def read_partitions(reader, sector_size: int | None = None) -> PartitionTable:
    """Parse whatever partition table ``reader`` has (GPT preferred over MBR)."""
    ss = sector_size or getattr(reader, "sector_size", 512)
    mbr = _safe_read(reader, 0, 512)
    table = PartitionTable(scheme="none", sector_size=ss)

    protective = False
    mbr_entries: list[Partition] = []
    if len(mbr) >= 512 and mbr[510:512] == MBR_SIGNATURE:
        mbr_entries, protective = _parse_mbr(mbr, ss)
    elif mbr:
        table.notes.append("no valid MBR signature (0x55AA) at sector 0")

    gpt = _parse_gpt(reader, ss)
    if gpt is not None:
        gpt.notes = table.notes + gpt.notes
        if not protective and mbr_entries:
            gpt.notes.append("GPT present but MBR is not protective (hybrid disk?)")
        return gpt

    if mbr_entries:
        table.scheme = "mbr"
        table.partitions = mbr_entries
        table.partitions.extend(_walk_extended(reader, mbr_entries, ss))
        for i, p in enumerate(table.partitions, start=1):
            p.index = i
    elif protective:
        table.notes.append("protective MBR found but no usable GPT header")
    return table


# --------------------------------------------------------------------------- MBR
def _parse_mbr(sector: bytes, ss: int) -> tuple[list[Partition], bool]:
    parts: list[Partition] = []
    protective = False
    for i in range(4):
        off = 446 + i * 16
        status, ptype = sector[off], sector[off + 4]
        lba, count = struct.unpack_from("<II", sector, off + 8)
        if ptype == PROTECTIVE_MBR_TYPE:
            protective = True
        if ptype == 0 or count == 0:
            continue
        parts.append(
            Partition(
                index=i + 1,
                start=lba * ss,
                size=count * ss,
                kind=MBR_TYPE_NAMES.get(ptype, f"unknown 0x{ptype:02X}"),
                scheme="mbr",
                type_id=f"0x{ptype:02X}",
                bootable=status == 0x80,
            )
        )
    return parts, protective


def _walk_extended(reader, primaries: list[Partition], ss: int, limit: int = 128) -> list[Partition]:
    """Follow the EBR linked list of a DOS extended partition."""
    out: list[Partition] = []
    ext = next((p for p in primaries if _mbr_type_int(p) in EXTENDED_TYPES), None)
    if ext is None:
        return out
    base = ext.start
    cursor = base
    seen: set[int] = set()
    while cursor and cursor not in seen and len(out) < limit:
        seen.add(cursor)
        data = _safe_read(reader, cursor, 512)
        if len(data) < 512 or data[510:512] != MBR_SIGNATURE:
            break
        ptype = data[446 + 4]
        lba, count = struct.unpack_from("<II", data, 446 + 8)
        if count:
            out.append(
                Partition(
                    index=0,
                    start=cursor + lba * ss,
                    size=count * ss,
                    kind=MBR_TYPE_NAMES.get(ptype, f"unknown 0x{ptype:02X}"),
                    scheme="ebr",
                    type_id=f"0x{ptype:02X}",
                    bootable=data[446] == 0x80,
                )
            )
        nxt_lba, nxt_count = struct.unpack_from("<II", data, 462 + 8)
        cursor = base + nxt_lba * ss if nxt_count else 0
    return out


def _mbr_type_int(p: Partition) -> int:
    try:
        return int(p.type_id, 16)
    except ValueError:
        return -1


# --------------------------------------------------------------------------- GPT
def _parse_gpt(reader, ss: int) -> PartitionTable | None:
    for which, lba in (("primary", 1), ("backup", -1)):
        offset = lba * ss if lba >= 0 else max(0, getattr(reader, "size", 0) - ss)
        header = _safe_read(reader, offset, ss)
        if len(header) < 92 or header[:8] != GPT_SIGNATURE:
            continue
        table = _read_gpt_header(reader, header, ss, which)
        if table is not None:
            return table
    return None


def _read_gpt_header(reader, header: bytes, ss: int, which: str) -> PartitionTable | None:
    (
        _sig, _rev, hdr_size, hdr_crc, _res, _cur_lba, _bak_lba,
        _first_usable, _last_usable,
    ) = struct.unpack_from("<8sIIIIQQQQ", header, 0)
    disk_guid = _guid(header[56:72])
    entries_lba, num_entries, entry_size, entries_crc = struct.unpack_from("<QIII", header, 72)

    notes: list[str] = []
    if 92 <= hdr_size <= len(header):
        check = bytearray(header[:hdr_size])
        check[16:20] = b"\0\0\0\0"
        if zlib.crc32(bytes(check)) & 0xFFFFFFFF != hdr_crc:
            notes.append(f"{which} GPT header CRC mismatch — header may be damaged")
    else:
        notes.append(f"{which} GPT header size {hdr_size} is implausible")

    if not (0 < num_entries <= 4096) or not (128 <= entry_size <= 4096):
        return None
    raw = _safe_read(reader, entries_lba * ss, num_entries * entry_size)
    if len(raw) < num_entries * entry_size:
        notes.append(f"{which} GPT entry array is truncated (unreadable area?)")
    elif zlib.crc32(raw) & 0xFFFFFFFF != entries_crc:
        notes.append(f"{which} GPT partition entries CRC mismatch")

    parts: list[Partition] = []
    for i in range(num_entries):
        off = i * entry_size
        if off + 128 > len(raw):
            break
        type_guid = raw[off : off + 16]
        if type_guid == b"\0" * 16:
            continue
        first, last = struct.unpack_from("<QQ", raw, off + 32)
        if last < first:
            continue
        name = raw[off + 56 : off + 128].decode("utf-16-le", "replace").split("\0")[0]
        tid = _guid(type_guid)
        parts.append(
            Partition(
                index=i + 1,
                start=first * ss,
                size=(last - first + 1) * ss,
                kind=GPT_TYPE_NAMES.get(tid, "unknown GPT type"),
                scheme="gpt",
                name=name,
                type_id=tid,
                guid=_guid(raw[off + 16 : off + 32]),
            )
        )
    if which == "backup":
        notes.append("primary GPT unusable — partitions read from the backup GPT")
    return PartitionTable(
        scheme="gpt", partitions=parts, sector_size=ss, disk_guid=disk_guid, notes=notes
    )


def _guid(raw: bytes) -> str:
    if len(raw) != 16:
        return ""
    return str(uuid.UUID(bytes_le=raw))


def _safe_read(reader, pos: int, size: int) -> bytes:
    """Reads on a damaged disk are allowed to fail; callers treat that as 'absent'."""
    if pos < 0 or size <= 0:
        return b""
    try:
        return reader.pread(pos, size)
    except OSError:
        return b""
