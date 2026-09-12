"""In-memory doubles so the rescue engine can be tested without a dying disk."""

from __future__ import annotations

import errno

from drescue.device import DeviceReadError


class FaultyReader:
    """A byte buffer with configurable unreadable sectors.

    ``bad_sectors`` holds sector indices that raise EIO.  A read is refused if
    it *touches* any bad sector — exactly how a real drive fails a multi-sector
    request.  ``transient`` sectors fail only the first ``flaky_reads`` times,
    modelling sectors that a retry pass can still recover.
    """

    def __init__(self, data: bytes, bad_sectors=(), sector_size: int = 512,
                 transient: dict[int, int] | None = None) -> None:
        self.data = bytearray(data)
        self.size = len(data)
        self.sector_size = sector_size
        self.bad = set(bad_sectors)
        self.transient = dict(transient or {})
        self.reads: list[tuple[int, int]] = []
        self.error_reads = 0
        self.dropped_cache = 0

    def _sectors(self, pos: int, size: int):
        first = pos // self.sector_size
        last = (pos + size - 1) // self.sector_size
        return range(first, last + 1)

    def pread(self, pos: int, size: int) -> bytes:
        if pos >= self.size:
            return b""
        size = min(size, self.size - pos)
        self.reads.append((pos, size))
        for sec in self._sectors(pos, size):
            if sec in self.bad:
                self.error_reads += 1
                raise DeviceReadError(errno.EIO, f"simulated bad sector {sec}")
            if self.transient.get(sec, 0) > 0:
                self.transient[sec] -= 1
                self.error_reads += 1
                raise DeviceReadError(errno.EIO, f"simulated flaky sector {sec}")
        return bytes(self.data[pos : pos + size])

    def drop_cache(self, pos: int = 0, size: int = 0) -> None:
        self.dropped_cache += 1

    def close(self) -> None:
        pass


class MemoryWriter:
    """Image destination backed by a bytearray, zero-filled where nothing landed."""

    def __init__(self, size: int) -> None:
        self.data = bytearray(size)
        self.written = bytearray(size)  # 1 where a byte was actually stored

    def pwrite(self, pos: int, data: bytes) -> int:
        self.data[pos : pos + len(data)] = data
        self.written[pos : pos + len(data)] = b"\x01" * len(data)
        return len(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass
