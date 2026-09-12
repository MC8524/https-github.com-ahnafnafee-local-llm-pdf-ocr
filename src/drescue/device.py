"""Raw block access: size/sector probing, aligned reads, sparse-aware writes.

Everything the rescue engine touches goes through :class:`Reader` /
:class:`Writer`, which keeps the algorithm testable against ordinary files and
in-memory fakes instead of requiring a dying disk.
"""

from __future__ import annotations

import errno
import mmap
import os
import stat
from typing import Protocol

# Linux ioctls.  Encoded here rather than hard-coded so the numbers are auditable.
_IOC_NRBITS, _IOC_TYPEBITS, _IOC_SIZEBITS = 8, 8, 14
_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS
_IOC_READ = 2


def _ioc(direction: int, typ: int, nr: int, size: int) -> int:
    return (
        (direction << _IOC_DIRSHIFT)
        | (typ << _IOC_TYPESHIFT)
        | (nr << _IOC_NRSHIFT)
        | (size << _IOC_SIZESHIFT)
    )


BLKSSZGET = _ioc(0, 0x12, 104, 0)  # _IO(0x12, 104)   logical sector size (int)
BLKGETSIZE64 = _ioc(_IOC_READ, 0x12, 114, 8)  # _IOR(0x12, 114, size_t)

DEFAULT_SECTOR_SIZE = 512

#: Errors that mean "this region of the medium is unreadable", not "you asked wrong".
MEDIUM_ERRNOS = frozenset(
    e
    for e in (
        getattr(errno, "EIO", None),
        getattr(errno, "ENXIO", None),
        getattr(errno, "ENODATA", None),
        getattr(errno, "EILSEQ", None),
        getattr(errno, "ETIMEDOUT", None),
        getattr(errno, "EREMOTEIO", None),
        getattr(errno, "EBADE", None),
    )
    if e is not None
)


class DeviceReadError(OSError):
    """A read failed on the medium (as opposed to a programming error)."""


class Reader(Protocol):  # pragma: no cover - structural type
    size: int
    sector_size: int

    def pread(self, pos: int, size: int) -> bytes: ...
    def close(self) -> None: ...


def probe_size(fd: int) -> int:
    """Byte size of the object behind ``fd`` (regular file or block device)."""
    st = os.fstat(fd)
    if stat.S_ISREG(st.st_mode):
        return st.st_size
    if stat.S_ISBLK(st.st_mode):
        try:
            import array
            import fcntl

            buf = array.array("Q", [0])
            fcntl.ioctl(fd, BLKGETSIZE64, buf, True)
            if buf[0]:
                return int(buf[0])
        except (OSError, ImportError, ValueError):
            pass
    # Works for block devices and anything else seekable.
    cur = os.lseek(fd, 0, os.SEEK_CUR)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.lseek(fd, cur, os.SEEK_SET)


def probe_sector_size(fd: int, default: int = DEFAULT_SECTOR_SIZE) -> int:
    st = os.fstat(fd)
    if stat.S_ISBLK(st.st_mode):
        try:
            import array
            import fcntl

            buf = array.array("i", [0])
            fcntl.ioctl(fd, BLKSSZGET, buf, True)
            if buf[0] > 0:
                return int(buf[0])
        except (OSError, ImportError, ValueError):
            pass
    return default


class BlockReader:
    """Read-only view of a device or image file.

    ``direct=True`` bypasses the page cache (``O_DIRECT``), which matters on a
    failing disk: otherwise a retry can be served from cache and a bad sector
    looks recovered when it is not.  Direct reads require sector-aligned
    offsets/lengths, handled transparently here.
    """

    def __init__(self, path: str | os.PathLike[str], *, direct: bool = False,
                 sector_size: int | None = None) -> None:
        self.path = os.fspath(path)
        flags = os.O_RDONLY
        odirect = getattr(os, "O_DIRECT", 0)
        self.direct = bool(direct and odirect)
        if self.direct:
            flags |= odirect
        try:
            self.fd = os.open(self.path, flags)
        except OSError:
            if self.direct:  # filesystem may not support O_DIRECT (tmpfs, etc.)
                self.direct = False
                self.fd = os.open(self.path, os.O_RDONLY)
            else:
                raise
        self.size = probe_size(self.fd)
        self.sector_size = sector_size or probe_sector_size(self.fd)
        self._buf: mmap.mmap | None = None
        self._buf_len = 0

    # ------------------------------------------------------------------ reads
    def pread(self, pos: int, size: int) -> bytes:
        """Read exactly ``size`` bytes at ``pos`` (clipped at EOF).

        Raises :class:`DeviceReadError` on a medium error; a short read at the
        end of the device is not an error.
        """
        if size <= 0:
            return b""
        if pos >= self.size:
            return b""
        size = min(size, self.size - pos)
        try:
            if self.direct:
                return self._pread_direct(pos, size)
            data = os.pread(self.fd, size, pos)
        except OSError as exc:
            raise _as_read_error(exc, pos, size) from exc
        return data

    def _pread_direct(self, pos: int, size: int) -> bytes:
        ss = self.sector_size
        lo = pos - (pos % ss)
        # Round up past EOF on purpose: O_DIRECT demands sector-multiple lengths,
        # and a short read is tolerated as long as the requested span arrived.
        hi = ((pos + size + ss - 1) // ss) * ss
        need = hi - lo
        buf = self._get_buffer(need)
        view = memoryview(buf)[:need]
        n = os.preadv(self.fd, [view], lo)
        if n < need and lo + n < pos + size:
            raise DeviceReadError(errno.EIO, "short direct read", self.path)
        return bytes(view[pos - lo : pos - lo + size])

    def _get_buffer(self, need: int) -> mmap.mmap:
        # mmap allocations are page-aligned, which satisfies O_DIRECT.
        if self._buf is None or self._buf_len < need:
            if self._buf is not None:
                self._buf.close()
            self._buf = mmap.mmap(-1, max(need, 1 << 20))
            self._buf_len = len(self._buf)
        return self._buf

    def drop_cache(self, pos: int = 0, size: int = 0) -> None:
        """Best-effort page-cache drop so retries really hit the medium."""
        fadvise = getattr(os, "posix_fadvise", None)
        if fadvise is None:
            return
        try:
            fadvise(self.fd, pos, size, os.POSIX_FADV_DONTNEED)
        except OSError:
            pass

    def close(self) -> None:
        if getattr(self, "fd", -1) >= 0:
            os.close(self.fd)
            self.fd = -1
        if self._buf is not None:
            self._buf.close()
            self._buf = None

    def __enter__(self) -> "BlockReader":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class BlockWriter:
    """Destination image file or device."""

    def __init__(self, path: str | os.PathLike[str], *, size: int | None = None,
                 truncate: bool = False, sync: bool = False) -> None:
        self.path = os.fspath(path)
        flags = os.O_WRONLY | os.O_CREAT
        if truncate:
            flags |= os.O_TRUNC
        self.fd = os.open(self.path, flags, 0o644)
        st = os.fstat(self.fd)
        self.is_regular = stat.S_ISREG(st.st_mode)
        self.sync = sync
        if size is not None and self.is_regular and size > st.st_size:
            # Sparse-allocate: no blocks consumed until written.
            os.ftruncate(self.fd, size)

    def pwrite(self, pos: int, data: bytes) -> int:
        written = 0
        while written < len(data):
            written += os.pwrite(self.fd, data[written:], pos + written)
        if self.sync:
            os.fsync(self.fd)
        return written

    def flush(self) -> None:
        try:
            os.fsync(self.fd)
        except OSError:
            pass

    def close(self) -> None:
        if getattr(self, "fd", -1) >= 0:
            self.flush()
            os.close(self.fd)
            self.fd = -1

    def __enter__(self) -> "BlockWriter":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _as_read_error(exc: OSError, pos: int, size: int) -> OSError:
    if exc.errno in MEDIUM_ERRNOS:
        err = DeviceReadError(exc.errno, f"read failed at 0x{pos:x} (0x{size:x} bytes)")
        err.filename = getattr(exc, "filename", None)
        return err
    return exc
