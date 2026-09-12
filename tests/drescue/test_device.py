import os

import pytest

from drescue.device import (
    BLKGETSIZE64,
    BLKSSZGET,
    BlockReader,
    BlockWriter,
    DeviceReadError,
    probe_sector_size,
    probe_size,
)


@pytest.fixture
def sample(tmp_path):
    p = tmp_path / "src.bin"
    p.write_bytes(bytes(range(256)) * 40)  # 10240 bytes
    return p


def test_ioctl_numbers_match_the_linux_kernel_definitions():
    # BLKSSZGET  = _IO(0x12, 104);  BLKGETSIZE64 = _IOR(0x12, 114, size_t)
    assert BLKSSZGET == 0x1268
    assert BLKGETSIZE64 == 0x80081272


def test_probe_size_and_sector_size_on_a_regular_file(sample):
    fd = os.open(sample, os.O_RDONLY)
    try:
        assert probe_size(fd) == 10240
        assert probe_sector_size(fd) == 512
        assert os.lseek(fd, 0, os.SEEK_CUR) == 0  # probing must not move the cursor
    finally:
        os.close(fd)


def test_pread_returns_exact_bytes(sample):
    with BlockReader(sample) as r:
        assert r.size == 10240
        assert r.pread(0, 4) == bytes([0, 1, 2, 3])
        assert r.pread(256, 2) == bytes([0, 1])


def test_pread_is_clipped_at_the_end_of_the_device(sample):
    with BlockReader(sample) as r:
        assert len(r.pread(10000, 4096)) == 240
        assert r.pread(10240, 512) == b""
        assert r.pread(0, 0) == b""


def test_direct_mode_reads_the_same_bytes(sample):
    with BlockReader(sample) as plain, BlockReader(sample, direct=True) as direct:
        for pos, size in ((0, 512), (1, 4095), (10000, 240), (511, 2)):
            assert direct.pread(pos, size) == plain.pread(pos, size)


def test_direct_mode_degrades_gracefully_when_unsupported(sample, monkeypatch):
    real_open = os.open

    def fake_open(path, flags, *rest):
        if flags & getattr(os, "O_DIRECT", 0):
            raise OSError(22, "O_DIRECT unsupported")
        return real_open(path, flags, *rest)

    monkeypatch.setattr(os, "open", fake_open)
    with BlockReader(sample, direct=True) as r:
        assert r.direct is False
        assert len(r.pread(0, 512)) == 512


def test_medium_errors_are_raised_as_device_read_errors(sample, monkeypatch):
    def boom(fd, size, pos):
        raise OSError(5, "I/O error")  # EIO

    monkeypatch.setattr(os, "pread", boom)
    with BlockReader(sample) as r:
        with pytest.raises(DeviceReadError):
            r.pread(0, 512)


def test_programming_errors_are_not_disguised_as_medium_errors(sample, monkeypatch):
    def boom(fd, size, pos):
        raise OSError(22, "Invalid argument")  # EINVAL

    monkeypatch.setattr(os, "pread", boom)
    with BlockReader(sample) as r:
        with pytest.raises(OSError) as exc:
            r.pread(0, 512)
        assert not isinstance(exc.value, DeviceReadError)


def test_writer_preallocates_sparsely_and_writes_at_offsets(tmp_path):
    out = tmp_path / "img.bin"
    with BlockWriter(out, size=1 << 20) as w:
        w.pwrite(4096, b"hello")
    assert out.stat().st_size == 1 << 20
    assert out.read_bytes()[4096:4101] == b"hello"
    # Nothing else was touched, and the file stayed sparse.
    assert out.stat().st_blocks * 512 < (1 << 20)


def test_drop_cache_is_best_effort(sample):
    with BlockReader(sample) as r:
        r.drop_cache(0, 512)  # must never raise
