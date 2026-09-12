"""Filesystem identification.

Where the environment provides an independent implementation (``mkfs.ext4`` to
build the volume, ``blkid`` to identify it) the parser is cross-checked against
it.  NTFS/exFAT are exercised against boot sectors built from their documented
layouts: ``blkid`` deliberately refuses a bare boot sector with no metadata
behind it, while a recovery tool must still recognise one, so the two cannot be
compared there.
"""

import shutil
import subprocess

import pytest

from drescue.device import BlockReader
from drescue.scan import find_lost_filesystems, identify_filesystem

from . import samples

MiB = 1024 * 1024


def _write(path, data, size):
    with open(path, "wb") as fh:
        fh.truncate(size)
        fh.seek(0)
        fh.write(data)
    return str(path)


@pytest.fixture(scope="module")
def ext4_image(tmp_path_factory):
    mkfs = shutil.which("mkfs.ext4") or "/sbin/mkfs.ext4"
    if not shutil.which(mkfs):
        pytest.skip("mkfs.ext4 not available")
    path = tmp_path_factory.mktemp("fs") / "ext4.img"
    path.write_bytes(b"")
    with open(path, "wb") as fh:
        fh.truncate(16 * MiB)
    subprocess.run([mkfs, "-q", "-F", "-L", "DRESCUE", "-U",
                    "11112222-3333-4444-5555-666677778888", str(path)], check=True)
    return str(path)


def test_identifies_a_real_ext4_volume(ext4_image):
    with BlockReader(ext4_image) as r:
        fs = identify_filesystem(r)
    assert fs is not None
    assert fs.kind == "ext4"
    assert fs.label == "DRESCUE"
    assert fs.uuid == "11112222-3333-4444-5555-666677778888"
    assert fs.block_size in (1024, 4096)
    assert fs.size == 16 * MiB


@pytest.mark.skipif(shutil.which("blkid") is None, reason="blkid not installed")
def test_agrees_with_blkid_about_ext4(ext4_image):
    out = subprocess.run(["blkid", "-p", "-o", "export", ext4_image],
                         capture_output=True, text=True).stdout
    props = dict(line.split("=", 1) for line in out.strip().splitlines() if "=" in line)
    with BlockReader(ext4_image) as r:
        fs = identify_filesystem(r)
    assert props["TYPE"] == fs.kind
    assert props["LABEL"] == fs.label
    assert props["UUID"] == fs.uuid
    assert int(props["BLOCK_SIZE"]) == fs.block_size


@pytest.mark.skipif(shutil.which("blkid") is None, reason="blkid not installed")
def test_agrees_with_blkid_about_fat32(tmp_path):
    path = _write(tmp_path / "fat.img", samples.fat32_boot_sector(), 32 * MiB)
    out = subprocess.run(["blkid", "-p", "-o", "export", path],
                         capture_output=True, text=True).stdout
    props = dict(line.split("=", 1) for line in out.strip().splitlines() if "=" in line)
    with BlockReader(path) as r:
        fs = identify_filesystem(r)
    assert props["VERSION"] == fs.kind == "FAT32"
    assert props["LABEL_FATBOOT"] == fs.label == "FATVOL"
    assert props["UUID"].replace("-", "") == fs.uuid
    assert int(props["FSSIZE"]) == fs.size


def test_identifies_an_ntfs_boot_sector(tmp_path):
    path = _write(tmp_path / "ntfs.img", samples.ntfs_boot_sector(), 16 * MiB)
    with BlockReader(path) as r:
        fs = identify_filesystem(r)
    assert fs.kind == "NTFS"
    assert fs.size == 16 * MiB
    assert fs.block_size == 4096
    assert fs.uuid == "1122334455667788"
    assert fs.details["mft_cluster"] == 4


def test_identifies_an_exfat_boot_sector(tmp_path):
    path = _write(tmp_path / "ex.img", samples.exfat_boot_sector(), 32 * MiB)
    with BlockReader(path) as r:
        fs = identify_filesystem(r)
    assert fs.kind == "exFAT"
    assert fs.size == 32 * MiB
    assert fs.block_size == 4096


def test_rejects_a_lookalike_with_implausible_geometry(tmp_path):
    """A stray "NTFS    " string must not be reported as a volume."""
    sector = bytearray(samples.ntfs_boot_sector())
    sector[0x0B:0x0D] = (777).to_bytes(2, "little")  # impossible sector size
    path = _write(tmp_path / "fake.img", bytes(sector), MiB)
    with BlockReader(path) as r:
        assert identify_filesystem(r) is None


def test_unknown_content_is_not_identified(tmp_path):
    path = _write(tmp_path / "noise.img", bytes(range(256)) * 64, MiB)
    with BlockReader(path) as r:
        assert identify_filesystem(r) is None


def test_finds_a_volume_with_no_partition_entry(tmp_path, ext4_image):
    """The DMDE-style sweep: a filesystem whose partition table entry is gone."""
    ext4 = open(ext4_image, "rb").read()
    path = tmp_path / "lost.img"
    with open(path, "wb") as fh:
        fh.truncate(64 * MiB)
        fh.seek(20 * MiB)
        fh.write(ext4)
        fh.seek(48 * MiB)
        fh.write(samples.fat32_boot_sector(label="LOST"))
    with BlockReader(path) as r:
        found = list(find_lost_filesystems(r))
    by_offset = {f.offset: f for f in found}
    assert 20 * MiB in by_offset and by_offset[20 * MiB].kind == "ext4"
    assert 48 * MiB in by_offset and by_offset[48 * MiB].label == "LOST"


def test_sweep_suppresses_volumes_already_covered_by_the_partition_table(tmp_path, ext4_image):
    ext4 = open(ext4_image, "rb").read()
    path = tmp_path / "known.img"
    with open(path, "wb") as fh:
        fh.truncate(64 * MiB)
        fh.seek(20 * MiB)
        fh.write(ext4)
    with BlockReader(path) as r:
        found = list(find_lost_filesystems(r, known=[(20 * MiB, 16 * MiB)]))
    assert found == []


def test_sweep_finds_a_volume_straddling_a_chunk_boundary(tmp_path, ext4_image):
    ext4 = open(ext4_image, "rb").read()
    path = tmp_path / "edge.img"
    chunk = 1 * MiB
    offset = chunk - 1024  # the ext superblock magic lands in the next chunk
    with open(path, "wb") as fh:
        fh.truncate(8 * MiB)
        fh.seek(offset)
        fh.write(ext4)
    with BlockReader(path) as r:
        found = list(find_lost_filesystems(r, chunk_size=chunk))
    assert [f.offset for f in found] == [offset]
