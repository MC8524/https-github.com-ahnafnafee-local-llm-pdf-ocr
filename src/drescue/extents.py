"""Extent map: the core data structure of the rescue engine.

An :class:`ExtentMap` is a contiguous, gap-free, non-overlapping sequence of
``(pos, size, status)`` records covering a byte range of a device.  It is the
in-memory form of a GNU ddrescue *mapfile* and every phase of the rescue
algorithm is expressed as "read the areas with status X, rewrite them as Y".

Statuses use the same single characters as GNU ddrescue so the on-disk mapfile
stays interchangeable with it.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence

# Block status characters (identical to GNU ddrescue's mapfile alphabet).
NON_TRIED = "?"
NON_TRIMMED = "*"
NON_SCRAPED = "/"
BAD = "-"
FINISHED = "+"

ALL_STATUSES = (NON_TRIED, NON_TRIMMED, NON_SCRAPED, BAD, FINISHED)

STATUS_NAMES = {
    NON_TRIED: "non-tried",
    NON_TRIMMED: "non-trimmed",
    NON_SCRAPED: "non-scraped",
    BAD: "bad-sector",
    FINISHED: "finished",
}

#: Statuses that still hold recoverable data (i.e. work is not done).
PENDING_STATUSES = (NON_TRIED, NON_TRIMMED, NON_SCRAPED, BAD)


@dataclass
class Extent:
    pos: int
    size: int
    status: str

    @property
    def end(self) -> int:
        return self.pos + self.size

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Extent(0x{self.pos:x}, 0x{self.size:x}, {self.status!r})"


Range = tuple[int, int]


def clip(ranges: Iterable[Range], domain: Sequence[Range] | None) -> Iterator[Range]:
    """Intersect ``ranges`` with ``domain``; ``None`` domain means "everything"."""
    if domain is None:
        yield from ((p, s) for p, s in ranges if s > 0)
        return
    dom = sorted(domain)
    for pos, size in ranges:
        if size <= 0:
            continue
        end = pos + size
        for dpos, dsize in dom:
            lo = max(pos, dpos)
            hi = min(end, dpos + dsize)
            if hi > lo:
                yield lo, hi - lo


class ExtentMap:
    """Ordered, merged, contiguous list of extents."""

    __slots__ = ("_ext",)

    def __init__(self, extents: Iterable[Extent] | None = None) -> None:
        self._ext: list[Extent] = list(extents or ())
        if self._ext:
            self._validate()

    # ------------------------------------------------------------------ ctors
    @classmethod
    def covering(cls, pos: int, size: int, status: str = NON_TRIED) -> "ExtentMap":
        if size <= 0:
            return cls()
        return cls([Extent(pos, size, status)])

    # ------------------------------------------------------------- properties
    @property
    def extents(self) -> list[Extent]:
        return self._ext

    @property
    def start(self) -> int:
        return self._ext[0].pos if self._ext else 0

    @property
    def end(self) -> int:
        return self._ext[-1].end if self._ext else 0

    @property
    def size(self) -> int:
        return self.end - self.start

    def __len__(self) -> int:
        return len(self._ext)

    def __iter__(self) -> Iterator[Extent]:
        return iter(self._ext)

    # ---------------------------------------------------------------- queries
    def _index(self, pos: int) -> int:
        """Index of the extent containing ``pos`` (clamped to the map)."""
        if not self._ext:
            raise IndexError("empty extent map")
        i = bisect_right(self._ext, pos, key=lambda e: e.pos) - 1
        return max(0, min(i, len(self._ext) - 1))

    def status_at(self, pos: int) -> str:
        return self._ext[self._index(pos)].status

    def ranges(self, *statuses: str, domain: Sequence[Range] | None = None) -> Iterator[Range]:
        """Yield ``(pos, size)`` for every extent whose status is in ``statuses``."""
        wanted = set(statuses) if statuses else set(ALL_STATUSES)
        raw = ((e.pos, e.size) for e in self._ext if e.status in wanted)
        yield from clip(raw, domain)

    def bytes_with(self, *statuses: str, domain: Sequence[Range] | None = None) -> int:
        return sum(s for _, s in self.ranges(*statuses, domain=domain))

    def totals(self, domain: Sequence[Range] | None = None) -> dict[str, int]:
        if domain is None:  # single pass, the common case
            out = dict.fromkeys(ALL_STATUSES, 0)
            for e in self._ext:
                out[e.status] += e.size
            return out
        return {st: self.bytes_with(st, domain=domain) for st in ALL_STATUSES}

    def is_done(self, domain: Sequence[Range] | None = None) -> bool:
        return self.bytes_with(*PENDING_STATUSES, domain=domain) == 0

    # --------------------------------------------------------------- mutation
    def _split_at(self, pos: int) -> int:
        """Ensure an extent boundary exists at ``pos``; return its index.

        Returns ``len(self._ext)`` when ``pos`` is at (or past) the end.
        """
        if not self._ext or pos <= self.start:
            return 0
        if pos >= self.end:
            return len(self._ext)
        i = self._index(pos)
        e = self._ext[i]
        if e.pos == pos:
            return i
        head = Extent(e.pos, pos - e.pos, e.status)
        tail = Extent(pos, e.end - pos, e.status)
        self._ext[i : i + 1] = [head, tail]
        return i + 1

    def set_status(self, pos: int, size: int, status: str) -> None:
        """Mark ``[pos, pos+size)`` with ``status``, splitting/merging as needed."""
        if size <= 0 or not self._ext:
            return
        pos = max(pos, self.start)
        end = min(pos + size, self.end)
        if end <= pos:
            return
        i = self._split_at(pos)
        j = self._split_at(end)
        self._ext[i:j] = [Extent(pos, end - pos, status)]
        self._merge_around(i)

    def _merge_around(self, i: int) -> None:
        lo = max(0, i - 1)
        hi = min(len(self._ext), i + 2)
        k = lo
        while k + 1 < hi and k + 1 < len(self._ext):
            a, b = self._ext[k], self._ext[k + 1]
            if a.status == b.status and a.end == b.pos:
                a.size += b.size
                del self._ext[k + 1]
                hi -= 1
            else:
                k += 1

    def merge_all(self) -> None:
        out: list[Extent] = []
        for e in self._ext:
            if out and out[-1].status == e.status and out[-1].end == e.pos:
                out[-1].size += e.size
            else:
                out.append(Extent(e.pos, e.size, e.status))
        self._ext = out

    def fill_gaps(self, pos: int, size: int, status: str = NON_TRIED) -> None:
        """Extend/patch the map so it contiguously covers ``[pos, pos+size)``."""
        end = pos + size
        if not self._ext:
            self._ext = [Extent(pos, size, status)] if size > 0 else []
            return
        out: list[Extent] = []
        cursor = pos
        for e in self._ext:
            if e.end <= pos or e.pos >= end:
                continue
            p, q = max(e.pos, pos), min(e.end, end)
            if p > cursor:
                out.append(Extent(cursor, p - cursor, status))
            out.append(Extent(p, q - p, e.status))
            cursor = q
        if cursor < end:
            out.append(Extent(cursor, end - cursor, status))
        self._ext = out
        self.merge_all()

    def copy(self) -> "ExtentMap":
        return ExtentMap(Extent(e.pos, e.size, e.status) for e in self._ext)

    # ------------------------------------------------------------ consistency
    def _validate(self) -> None:
        prev_end = None
        for e in self._ext:
            if e.size <= 0:
                raise ValueError(f"non-positive extent size at 0x{e.pos:x}")
            if e.status not in STATUS_NAMES:
                raise ValueError(f"unknown status {e.status!r}")
            if prev_end is not None and e.pos != prev_end:
                raise ValueError(
                    f"non-contiguous extent map: 0x{prev_end:x} -> 0x{e.pos:x}"
                )
            prev_end = e.end


def align_down(value: int, alignment: int) -> int:
    return value - (value % alignment)


def align_up(value: int, alignment: int) -> int:
    rem = value % alignment
    return value if rem == 0 else value + alignment - rem
