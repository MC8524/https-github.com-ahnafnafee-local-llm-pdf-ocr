"""Terminal rendering: live rescue status, map visualisation, human units.

Deliberately dependency-free — a recovery tool has to run from a rescue USB
stick where ``pip install`` is not an option.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from typing import Sequence, TextIO

from .extents import (
    ALL_STATUSES,
    BAD,
    FINISHED,
    NON_SCRAPED,
    NON_TRIED,
    NON_TRIMMED,
    STATUS_NAMES,
    ExtentMap,
    Range,
)
from .rescue import Stats

_UNITS = ("B", "kB", "MB", "GB", "TB", "PB")

#: Block characters + colours used by :func:`render_map`.
STATUS_GLYPH = {
    FINISHED: ("#", "\033[32m"),
    NON_TRIED: (".", "\033[90m"),
    NON_TRIMMED: ("*", "\033[33m"),
    NON_SCRAPED: ("/", "\033[35m"),
    BAD: ("X", "\033[31m"),
}
RESET = "\033[0m"


def human_bytes(n: float, decimals: int = 1) -> str:
    n = float(n)
    for unit in _UNITS:
        if abs(n) < 1000 or unit == _UNITS[-1]:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.{decimals}f} {unit}"
        n /= 1000.0
    return f"{n} B"  # pragma: no cover


def human_rate(n: float) -> str:
    return f"{human_bytes(n)}/s"


def human_time(seconds: float) -> str:
    seconds = int(max(0, seconds))
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def color_enabled(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def render_map(emap: ExtentMap, width: int = 64, domain: Sequence[Range] | None = None,
               color: bool = False) -> str:
    """One line of glyphs summarising the whole medium.

    Each cell shows the *worst* status in its slice, so a single bad sector in a
    gigabyte is never hidden by the surrounding good data.  Rendered in a single
    pass over the extents so it stays cheap on a map with many bad areas.
    """
    severity = {st: i for i, st in enumerate((BAD, NON_SCRAPED, NON_TRIMMED,
                                              NON_TRIED, FINISHED))}
    total = emap.size
    if total <= 0 or width <= 0:
        return ""
    base = emap.start
    worst: list[int | None] = [None] * width

    def mark(pos: int, size: int, status: str) -> None:
        rank = severity.get(status)
        if rank is None or size <= 0:
            return
        first = min(width - 1, (pos - base) * width // total)
        last = min(width - 1, (pos + size - 1 - base) * width // total)
        for cell in range(max(0, first), last + 1):
            current = worst[cell]
            if current is None or rank < current:
                worst[cell] = rank

    if domain is None:
        for e in emap:
            mark(e.pos, e.size, e.status)
    else:
        for st in ALL_STATUSES:
            for pos, size in emap.ranges(st, domain=domain):
                mark(pos, size, st)

    by_rank = {i: st for st, i in severity.items()}
    cells = []
    for rank in worst:
        st = by_rank[rank] if rank is not None else NON_TRIED
        glyph, col = STATUS_GLYPH[st]
        cells.append(f"{col}{glyph}{RESET}" if color else glyph)
    return "".join(cells)


def map_legend(color: bool = False) -> str:
    parts = []
    for st in (FINISHED, NON_TRIED, NON_TRIMMED, NON_SCRAPED, BAD):
        glyph, col = STATUS_GLYPH[st]
        g = f"{col}{glyph}{RESET}" if color else glyph
        parts.append(f"{g} {STATUS_NAMES[st]}")
    return "   ".join(parts)


def summary_lines(emap: ExtentMap, domain: Sequence[Range] | None = None) -> list[str]:
    totals = emap.totals(domain)
    size = sum(totals.values())
    out = []
    for st in ALL_STATUSES:
        pct = 100.0 * totals[st] / size if size else 0.0
        areas = sum(1 for _ in emap.ranges(st, domain=domain))
        out.append(
            f"  {STATUS_NAMES[st]:>12}: {human_bytes(totals[st]):>12}  "
            f"{pct:6.2f}%  ({areas} area{'s' if areas != 1 else ''})"
        )
    out.append(f"  {'total':>12}: {human_bytes(size):>12}")
    return out


class StatusPrinter:
    """ddrescue-style five-line live status block, redrawn in place."""

    LINES = 6

    def __init__(self, stream: TextIO | None = None, size: int = 0,
                 show_map: bool = True) -> None:
        self.stream = stream or sys.stderr
        self.size = size
        self.color = color_enabled(self.stream)
        self.tty = bool(getattr(self.stream, "isatty", lambda: False)())
        self.show_map = show_map and self.tty
        self._drawn = 0
        # Rendering the map walks every extent, so redraw it at most once a
        # second even though the counters update four times as often.
        self._map_cache = ""
        self._map_time = 0.0

    def update(self, stats: Stats, emap: ExtentMap | None = None,
               domain: Sequence[Range] | None = None) -> None:
        eta = _eta(stats)
        pct = 100.0 * stats.rescued / self.size if self.size else 0.0
        lines = [
            f"     phase: {stats.phase} (pass {stats.pass_no})"
            f"{'':4}  ipos: {human_bytes(stats.current_pos):>12}",
            f"   rescued: {human_bytes(stats.rescued):>12}   "
            f"non-trimmed: {human_bytes(stats.non_trimmed):>12}   "
            f"current rate: {human_rate(stats.current_rate):>12}",
            f" non-tried: {human_bytes(stats.non_tried):>12}   "
            f"non-scraped: {human_bytes(stats.non_scraped):>12}   "
            f"average rate: {human_rate(stats.average_rate):>12}",
            f"  pct done: {pct:11.2f}%   "
            f" bad-sector: {human_bytes(stats.bad):>12}   "
            f"   bad areas: {stats.bad_areas:>12}",
            f"  run time: {human_time(stats.run_time):>12}   "
            f"read errors: {stats.errors:>12}   "
            f"remaining ~: {eta:>12}",
        ]
        if self.show_map and emap is not None:
            now = time.monotonic()
            if not self._map_cache or now - self._map_time >= 1.0:
                width = max(16, min(shutil.get_terminal_size((80, 24)).columns - 8, 100))
                self._map_cache = render_map(emap, width, domain, self.color)
                self._map_time = now
            lines.append("       map: " + self._map_cache)
        self._draw(lines)

    def _draw(self, lines: list[str]) -> None:
        if self.tty:
            if self._drawn:
                self.stream.write(f"\033[{self._drawn}A")
            for line in lines:
                self.stream.write("\033[2K" + line + "\n")
            self._drawn = len(lines)
        else:
            self.stream.write(lines[1] + "\n")
        self.stream.flush()

    def finish(self) -> None:
        self.stream.write("\n")
        self.stream.flush()


def _eta(stats: Stats) -> str:
    remaining = stats.non_tried + stats.non_trimmed + stats.non_scraped
    rate = stats.current_rate or stats.average_rate
    if remaining <= 0:
        return "done"
    if rate <= 0:
        return "?"
    return human_time(remaining / rate)
