import shutil
import struct
import subprocess

import pytest

from drescue.device import BlockReader
from drescue.scan import read_partitions

from . import samples

MiB = 1024 * 1024
LINUX_GUID = "0fc63daf-8483-4772-8e79-3d69d8477de4"
EFI_GUID = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"


@pytest.fixture
def gpt_image(tmp_path):
    return samples.make_gpt_image(
        str(tmp_path / "gpt.img"),
        [(LINUX_GUID, "rootfs", 1 * MiB, 16 * MiB, None),
         (EFI_GUID, "ESP", 20 * MiB, 8 * MiB, None)],
        64 * MiB,
    )


@pytest.fixture
def mbr_image(tmp_path):
    return samples.make_mbr_image(
        str(tmp_path / "mbr.img"),
        [(0x83, 1 * MiB, 16 * MiB, None), (0x0C, 20 * MiB, 8 * MiB, None)],
        64 * MiB,
    )


def test_reads_a_gpt(gpt_image):
    with BlockReader(gpt_image) as r:
        table = read_partitions(r)
    assert table.scheme == "gpt"
    assert len(table) == 2
    first, second = table.partitions
    assert (first.start, first.size, first.name) == (1 * MiB, 16 * MiB, "rootfs")
    assert first.kind == "Linux filesystem"
    assert (second.start, second.size, second.name) == (20 * MiB, 8 * MiB, "ESP")
    assert second.kind == "EFI system"
    assert table.disk_guid
    assert not table.notes


def test_falls_back_to_the_backup_gpt_when_the_primary_is_destroyed(gpt_image):
    with open(gpt_image, "r+b") as fh:
        fh.seek(512)
        fh.write(b"\0" * 512)  # wipe the primary header
    with BlockReader(gpt_image) as r:
        table = read_partitions(r)
    assert table.scheme == "gpt"
    assert [p.name for p in table] == ["rootfs", "ESP"]
    assert any("backup" in n for n in table.notes)


def test_flags_a_corrupt_gpt_header_crc(gpt_image):
    with open(gpt_image, "r+b") as fh:
        fh.seek(512 + 56)  # inside the disk GUID: changes the body, not the CRC
        fh.write(b"\xff" * 4)
    with BlockReader(gpt_image) as r:
        table = read_partitions(r)
    assert any("CRC mismatch" in n for n in table.notes)


def test_reads_an_mbr(mbr_image):
    with BlockReader(mbr_image) as r:
        table = read_partitions(r)
    assert table.scheme == "mbr"
    assert [(p.start, p.size) for p in table] == [(1 * MiB, 16 * MiB), (20 * MiB, 8 * MiB)]
    assert table.partitions[0].kind == "Linux"
    assert table.partitions[0].bootable is True
    assert table.partitions[1].kind == "FAT32 LBA"


def test_walks_an_extended_partition_chain(tmp_path):
    path = str(tmp_path / "ext.img")
    samples.make_mbr_image(path, [(0x05, 1 * MiB, 32 * MiB, None)], 64 * MiB)
    # One EBR describing a 4 MiB logical partition, no next link.
    ebr = bytearray(512)
    ebr[446 + 4] = 0x83
    struct.pack_into("<II", ebr, 446 + 8, 2048, 8192)
    ebr[510:512] = b"\x55\xaa"
    with open(path, "r+b") as fh:
        fh.seek(1 * MiB)
        fh.write(ebr)
    with BlockReader(path) as r:
        table = read_partitions(r)
    logical = [p for p in table if p.scheme == "ebr"]
    assert len(logical) == 1
    assert logical[0].start == 1 * MiB + 2048 * 512
    assert logical[0].size == 8192 * 512


def test_unpartitioned_medium_reports_no_scheme(tmp_path):
    path = tmp_path / "raw.img"
    path.write_bytes(b"\0" * MiB)
    with BlockReader(path) as r:
        table = read_partitions(r)
    assert table.scheme == "none"
    assert len(table) == 0


def test_unreadable_sectors_do_not_crash_the_parser(tmp_path):
    from .fakes import FaultyReader

    path = samples.make_mbr_image(str(tmp_path / "m.img"),
                                  [(0x83, 1 * MiB, 4 * MiB, None)], 8 * MiB)
    data = open(path, "rb").read()
    table = read_partitions(FaultyReader(data, bad_sectors={0}))
    assert table.scheme == "none"  # sector 0 unreadable: nothing invented


@pytest.mark.skipif(shutil.which("partx") is None, reason="util-linux partx not installed")
@pytest.mark.parametrize("fixture", ["gpt_image", "mbr_image"])
def test_agrees_with_util_linux(request, fixture):
    """Cross-check the parser against an independent implementation."""
    path = request.getfixturevalue(fixture)
    out = subprocess.run(["partx", "-g", "-o", "START,SECTORS", path],
                         capture_output=True, text=True, check=True).stdout
    expected = [(int(a) * 512, int(b) * 512) for a, b in
                (line.split() for line in out.strip().splitlines())]
    with BlockReader(path) as r:
        got = [(p.start, p.size) for p in read_partitions(r)]
    assert got == expected
