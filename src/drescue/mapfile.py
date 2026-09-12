"""Read/write GNU ddrescue-compatible mapfiles (a.k.a. logfiles).

The format is deliberately kept byte-for-byte interchangeable with GNU
ddrescue >= 1.20 so an interrupted ``ddrescue`` run can be resumed by this tool
and vice versa:

    # Mapfile. Created by drescue 0.1.0
    # Command line: drescue rescue /dev/sdb disk.img disk.map
    # Start time:   2026-09-12 10:00:00
    # Current time: 2026-09-12 10:04:11
    # copying non-tried blocks... pass 1 (forwards)
    #      current_pos  current_status  current_pass
    0x00001000     ?               1
    #      pos        size  status
    0x00000000  0x00001000  +
    0x00001000  0x00000200  *

Writes are atomic (temp file + ``os.replace``) because the mapfile is the only
thing standing between an interrupted rescue and starting over.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Iterable

from .extents import ALL_STATUSES, Extent, ExtentMap

#: Characters valid in the *current status* line (superset of block statuses).
CURRENT_STATUSES = {
    "?": "copying non-tried blocks",
    "*": "trimming failed blocks",
    "/": "scraping failed blocks",
    "-": "retrying bad sectors",
    "F": "filling specified blocks",
    "G": "generating approximate mapfile",
    "+": "finished",
}


class MapfileError(ValueError):
    """Raised when a mapfile cannot be parsed."""


@dataclass
class Mapfile:
    """An extent map plus the resume bookkeeping ddrescue stores alongside it."""

    extents: ExtentMap = field(default_factory=ExtentMap)
    current_pos: int = 0
    current_status: str = "?"
    current_pass: int = 1
    command_line: str = ""
    start_time: float | None = None
    comments: list[str] = field(default_factory=list)

    # ----------------------------------------------------------------- parse
    @classmethod
    def parse(cls, text: str) -> "Mapfile":
        mf = cls()
        extents: list[Extent] = []
        status_seen = False
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                mf.comments.append(line)
                if "Command line:" in line:
                    mf.command_line = line.split("Command line:", 1)[1].strip()
                continue
            fields = line.split()
            if not status_seen:
                if len(fields) < 2 or fields[1] not in CURRENT_STATUSES:
                    raise MapfileError(
                        f"line {lineno}: expected a status line, got {line!r}"
                    )
                mf.current_pos = _int(fields[0], lineno)
                mf.current_status = fields[1]
                mf.current_pass = int(fields[2]) if len(fields) > 2 else 1
                status_seen = True
                continue
            if len(fields) < 3:
                raise MapfileError(f"line {lineno}: expected 'pos size status'")
            pos, size, st = _int(fields[0], lineno), _int(fields[1], lineno), fields[2]
            if st not in ALL_STATUSES:
                raise MapfileError(f"line {lineno}: unknown block status {st!r}")
            if size < 0:
                raise MapfileError(f"line {lineno}: negative size")
            if size:
                extents.append(Extent(pos, size, st))
        if not status_seen:
            raise MapfileError("mapfile has no status line")
        extents.sort(key=lambda e: e.pos)
        _check_contiguous(extents)
        mf.extents = ExtentMap(extents)
        mf.extents.merge_all()
        return mf

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "Mapfile":
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return cls.parse(fh.read())

    # ----------------------------------------------------------------- write
    def render(self, now: float | None = None) -> str:
        now = time.time() if now is None else now
        start = self.start_time if self.start_time is not None else now
        from . import __version__

        out = [
            f"# Mapfile. Created by drescue {__version__}",
            f"# Command line: {self.command_line}" if self.command_line else "# Command line:",
            f"# Start time:   {_stamp(start)}",
            f"# Current time: {_stamp(now)}",
            f"# {CURRENT_STATUSES.get(self.current_status, 'unknown')}"
            + (f"... pass {self.current_pass}" if self.current_status != "+" else ""),
            "#      current_pos  current_status  current_pass",
            f"0x{self.current_pos:08X}     {self.current_status}               {self.current_pass}",
            "#      pos        size  status",
        ]
        for e in self.extents:
            out.append(f"0x{e.pos:08X}  0x{e.size:08X}  {e.status}")
        return "\n".join(out) + "\n"

    def save(self, path: str | os.PathLike[str], now: float | None = None) -> None:
        """Atomically replace ``path`` with the current map."""
        path = os.fspath(path)
        tmp = f"{path}.tmp{os.getpid()}"
        data = self.render(now)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(fd, data.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, path)

    # ------------------------------------------------------------------ misc
    @classmethod
    def load_or_create(
        cls, path: str | os.PathLike[str], pos: int, size: int, command_line: str = ""
    ) -> "Mapfile":
        """Resume from ``path`` if it exists, else start a fresh map of the device.

        An existing map is extended (never truncated) to cover ``[pos, pos+size)``
        so re-imaging onto a larger device keeps prior results.
        """
        if os.path.exists(path) and os.path.getsize(path) > 0:
            mf = cls.load(path)
            mf.extents.fill_gaps(min(pos, mf.extents.start), max(pos + size, mf.extents.end) - min(pos, mf.extents.start))
            if command_line:
                mf.command_line = command_line
            return mf
        return cls(
            extents=ExtentMap.covering(pos, size),
            current_pos=pos,
            command_line=command_line,
            start_time=time.time(),
        )


def _int(token: str, lineno: int) -> int:
    try:
        return int(token, 0)
    except ValueError as exc:  # pragma: no cover - defensive
        raise MapfileError(f"line {lineno}: bad number {token!r}") from exc


def _check_contiguous(extents: Iterable[Extent]) -> None:
    prev = None
    for e in extents:
        if prev is not None and e.pos != prev:
            raise MapfileError(
                f"non-contiguous mapfile: gap/overlap at 0x{e.pos:x} (expected 0x{prev:x})"
            )
        prev = e.pos + e.size


def _stamp(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
