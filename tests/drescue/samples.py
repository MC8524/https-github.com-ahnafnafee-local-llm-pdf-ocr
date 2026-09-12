"""Small but *real* sample files used to exercise the carver's length logic."""

from __future__ import annotations

import io
import os
import sqlite3
import struct
import tempfile
import wave
import zipfile
import zlib


def png(width: int = 4, height: int = 4) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(
            ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
        )

    raw = b"".join(b"\x00" + bytes([(x * 37 + y * 11) % 256 for x in range(width)])
                   for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def jpeg(payload: bytes = b"\x11\x22\x33" * 40) -> bytes:
    """A structurally valid JPEG: SOI, APP0, SOS, entropy data (stuffed), EOI."""
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = b"\xff\xc0" + struct.pack(">H", 11) + b"\x08\x00\x08\x00\x08\x01\x01\x11\x00"
    sos = b"\xff\xda" + struct.pack(">H", 8) + b"\x01\x01\x00\x00\x3f\x00"
    # 0xFF bytes inside entropy-coded data must be byte-stuffed with 0x00.
    entropy = payload.replace(b"\xff", b"\xff\x00") + b"\xff\x00\xd9"
    return b"\xff\xd8" + app0 + sof + sos + entropy + b"\xff\xd9"


def gif() -> bytes:
    header = b"GIF89a" + struct.pack("<HH", 2, 2) + bytes([0x80, 0, 0])
    gct = b"\x00\x00\x00\xff\xff\xff"
    img = b"\x2c" + struct.pack("<HHHH", 0, 0, 2, 2) + b"\x00"
    data = b"\x02\x02\x4c\x01\x00"  # LZW min code size + one sub-block + terminator
    return header + gct + img + data + b"\x3b"


def wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x01\x02" * 200)
    return buf.getvalue()


def zip_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<document>hello</document>")
    return buf.getvalue()


def sqlite_db() -> bytes:
    path = tempfile.mktemp(suffix=".db")
    try:
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE t (a TEXT)")
        con.executemany("INSERT INTO t VALUES (?)", [(f"row{i}",) for i in range(50)])
        con.commit()
        con.close()
        with open(path, "rb") as fh:
            return fh.read()
    finally:
        if os.path.exists(path):
            os.unlink(path)


def bmp(width: int = 2, height: int = 2) -> bytes:
    pixels = b"\xff\x00\x00\x00\xff\x00\x00\x00" * height
    size = 54 + len(pixels)
    header = b"BM" + struct.pack("<IHHI", size, 0, 0, 54)
    dib = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
    return header + dib + pixels


# --------------------------------------------------------------- disk images
import uuid as _uuid  # noqa: E402

MBR_SIG = b"\x55\xaa"


def _mbr_entry(bootable: bool, ptype: int, start_lba: int, count: int) -> bytes:
    return (
        bytes([0x80 if bootable else 0x00])
        + b"\xfe\xff\xff"  # CHS first (obsolete, filled with the "use LBA" value)
        + bytes([ptype])
        + b"\xfe\xff\xff"  # CHS last
        + struct.pack("<II", start_lba, count)
    )


def make_mbr_image(path: str, partitions, size: int, sector: int = 512) -> str:
    """``partitions``: iterable of ``(ptype, start_bytes, size_bytes, payload|None)``."""
    with open(path, "wb") as fh:
        fh.truncate(size)
        table = b""
        for i, (ptype, start, psize, payload) in enumerate(partitions):
            table += _mbr_entry(i == 0, ptype, start // sector, psize // sector)
            if payload:
                fh.seek(start)
                fh.write(payload)
        table = table.ljust(64, b"\0")
        fh.seek(446)
        fh.write(table)
        fh.seek(510)
        fh.write(MBR_SIG)
    return path


def make_gpt_image(path: str, partitions, size: int, sector: int = 512) -> str:
    """Build a spec-conformant GPT disk (primary + backup, valid CRC32s).

    ``partitions``: iterable of ``(type_guid_str, name, start_bytes, size_bytes,
    payload|None)``.
    """
    entry_size, num_entries = 128, 128
    array_sectors = (entry_size * num_entries + sector - 1) // sector
    disk_guid = _uuid.uuid4()
    entries = bytearray()
    for type_guid, name, start, psize, payload in partitions:
        first = start // sector
        last = (start + psize) // sector - 1
        entries += (
            _uuid.UUID(type_guid).bytes_le
            + _uuid.uuid4().bytes_le
            + struct.pack("<QQQ", first, last, 0)
            + name.encode("utf-16-le").ljust(72, b"\0")[:72]
        )
    entries = bytes(entries).ljust(entry_size * num_entries, b"\0")
    entries_crc = zlib.crc32(entries) & 0xFFFFFFFF

    last_lba = size // sector - 1
    first_usable = 2 + array_sectors
    last_usable = last_lba - 1 - array_sectors

    def header(current: int, backup: int, entries_lba: int) -> bytes:
        body = (
            b"EFI PART"
            + struct.pack("<II", 0x00010000, 92)
            + struct.pack("<I", 0)  # CRC placeholder
            + struct.pack("<I", 0)  # reserved
            + struct.pack("<QQQQ", current, backup, first_usable, last_usable)
            + disk_guid.bytes_le
            + struct.pack("<QIII", entries_lba, num_entries, entry_size, entries_crc)
        )
        crc = zlib.crc32(body) & 0xFFFFFFFF
        return body[:16] + struct.pack("<I", crc) + body[20:]

    with open(path, "wb") as fh:
        fh.truncate(size)
        # Protective MBR covering the whole disk.
        fh.seek(446)
        fh.write(_mbr_entry(False, 0xEE, 1, min(last_lba, 0xFFFFFFFF)))
        fh.seek(510)
        fh.write(MBR_SIG)
        fh.seek(sector)
        fh.write(header(1, last_lba, 2).ljust(sector, b"\0"))
        fh.seek(2 * sector)
        fh.write(entries)
        fh.seek((last_lba - array_sectors) * sector)
        fh.write(entries)
        fh.seek(last_lba * sector)
        fh.write(header(last_lba, 1, last_lba - array_sectors).ljust(sector, b"\0"))
        for _t, _n, start, _s, payload in partitions:
            if payload:
                fh.seek(start)
                fh.write(payload)
    return path


# --------------------------------------------------- synthetic boot sectors
def ntfs_boot_sector(total_sectors: int = 32768, serial: int = 0x1122334455667788) -> bytes:
    s = bytearray(512)
    s[0:3] = b"\xeb\x52\x90"
    s[3:11] = b"NTFS    "
    struct.pack_into("<HB", s, 0x0B, 512, 8)  # bytes/sector, sectors/cluster
    s[0x15] = 0xF8  # media descriptor
    struct.pack_into("<HH", s, 0x18, 63, 255)  # sectors/track, heads
    struct.pack_into("<I", s, 0x24, 0x00800080)
    struct.pack_into("<Q", s, 0x28, total_sectors - 1)
    struct.pack_into("<QQ", s, 0x30, 4, total_sectors // 2)  # $MFT, $MFTMirr
    s[0x40] = 246  # clusters per MFT record (-10 => 1024 bytes)
    s[0x44] = 1
    struct.pack_into("<Q", s, 0x48, serial)
    s[510:512] = b"\x55\xaa"
    return bytes(s)


def fat32_boot_sector(total_sectors: int = 65536, label: str = "FATVOL",
                      serial: int = 0xAABBCCDD) -> bytes:
    s = bytearray(512)
    s[0:3] = b"\xeb\x58\x90"
    s[3:11] = b"mkfs.fat"
    struct.pack_into("<HBHBHHBHHHII", s, 0x0B,
                     512,   # bytes per sector
                     8,     # sectors per cluster
                     32,    # reserved sectors
                     2,     # number of FATs
                     0,     # root entries (0 on FAT32)
                     0,     # total sectors 16
                     0xF8,  # media
                     0,     # FAT size 16
                     63, 255,  # sectors per track, heads
                     0,     # hidden sectors
                     total_sectors)
    struct.pack_into("<IHHI", s, 0x24, 512, 0, 0, 2)  # FAT32 size, flags, ver, root clus
    struct.pack_into("<HH", s, 0x30, 1, 6)  # FSInfo, backup boot sector
    s[0x42] = 0x29  # extended boot signature
    struct.pack_into("<I", s, 0x43, serial)
    s[0x47:0x52] = label.encode().ljust(11)[:11]
    s[0x52:0x5A] = b"FAT32   "
    s[510:512] = b"\x55\xaa"
    return bytes(s)


def exfat_boot_sector(volume_length: int = 65536, serial: int = 0x12345678) -> bytes:
    s = bytearray(512)
    s[0:3] = b"\xeb\x76\x90"
    s[3:11] = b"EXFAT   "
    struct.pack_into("<QQ", s, 0x40, 0, volume_length)  # partition offset, volume length
    struct.pack_into("<IIII", s, 0x50, 128, 512, 2048, 8000)
    struct.pack_into("<I", s, 0x60, 4)  # root directory cluster
    struct.pack_into("<IHH", s, 0x64, serial, 0x0100, 0)
    s[0x6C] = 9  # bytes-per-sector shift  (512)
    s[0x6D] = 3  # sectors-per-cluster shift (8)
    s[0x6E] = 1  # number of FATs
    s[510:512] = b"\x55\xaa"
    return bytes(s)
