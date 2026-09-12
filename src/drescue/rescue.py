"""The rescue engine: copy → trim → scrape → retry.

The algorithm follows GNU ddrescue's proven strategy, which exists because a
dying drive has a *budget*: every read of a bad sector costs seconds and pushes
the head further towards death.  So:

1. **copy**    — read big clusters, and on the first error *run away*: mark the
                 cluster ``non-trimmed`` and skip ahead (doubling the skip on
                 consecutive errors).  Gets the healthy 99 % off the drive fast.
2. **trim**    — nibble at the edges of each failed cluster from both sides in
                 sector steps; what survives in the middle becomes ``non-scraped``.
3. **scrape**  — read the remaining middles sector by sector; whatever fails is
                 down to genuine ``bad-sector`` areas.
4. **retry**   — re-read only the bad sectors, alternating direction, N passes.

Every transition is written to the mapfile, so the job is interruptible and
resumable at any point — including across a power cycle or a different tool.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterator, Protocol, Sequence

from .extents import (
    BAD,
    FINISHED,
    NON_SCRAPED,
    NON_TRIED,
    NON_TRIMMED,
    ExtentMap,
    Range,
    align_down,
    align_up,
)
from .device import DeviceReadError
from .mapfile import Mapfile

KiB = 1024
MiB = 1024 * 1024


class Writable(Protocol):  # pragma: no cover - structural type
    def pwrite(self, pos: int, data: bytes) -> int: ...


@dataclass
class RescueConfig:
    sector_size: int = 512
    #: Sectors read per I/O during the copy phase (ddrescue's "cluster size").
    cluster_size: int = 128
    #: Bytes to jump ahead after a read error; doubles while errors continue.
    skip_size: int = 64 * KiB
    max_skip_size: int = 16 * MiB
    reverse: bool = False
    copy_passes: int = 3
    trim: bool = True
    scrape: bool = True
    #: Extra passes over bad sectors. ``-1`` means "until interrupted".
    retries: int = 1
    #: Abort after this many read errors (``None`` = unlimited).
    max_errors: int | None = None
    #: Abort once this many bytes are known bad (``None`` = unlimited).
    max_bad_bytes: int | None = None
    #: Throttle to this many bytes/second (``None`` = full speed).
    rate_limit: int | None = None
    #: Seconds between mapfile checkpoints.
    sync_interval: float = 30.0
    #: Restrict all work to these ``(pos, size)`` ranges.
    domain: Sequence[Range] | None = None
    #: Write this byte over unreadable areas instead of leaving them untouched.
    fill_bad: int | None = None

    def __post_init__(self) -> None:
        if self.sector_size <= 0 or self.sector_size & (self.sector_size - 1):
            raise ValueError("sector_size must be a positive power of two")
        if self.cluster_size < 1:
            raise ValueError("cluster_size must be >= 1")

    @property
    def cluster_bytes(self) -> int:
        return self.sector_size * self.cluster_size


@dataclass
class Stats:
    phase: str = "copy"
    pass_no: int = 1
    current_pos: int = 0
    rescued: int = 0
    non_tried: int = 0
    non_trimmed: int = 0
    non_scraped: int = 0
    bad: int = 0
    bad_areas: int = 0
    errors: int = 0
    read_bytes: int = 0
    start_time: float = field(default_factory=time.monotonic)
    run_time: float = 0.0
    current_rate: float = 0.0

    @property
    def average_rate(self) -> float:
        return self.read_bytes / self.run_time if self.run_time > 0 else 0.0

    @property
    def pending(self) -> int:
        return self.non_tried + self.non_trimmed + self.non_scraped + self.bad


ProgressCB = Callable[[Stats], None]
StopCB = Callable[[], bool]


class Rescuer:
    """Drives a :class:`Mapfile` from all-``non-tried`` to all-``finished``."""

    def __init__(
        self,
        reader,
        writer: Writable | None,
        mapfile: Mapfile,
        config: RescueConfig | None = None,
        *,
        mapfile_path: str | None = None,
        on_progress: ProgressCB | None = None,
        should_stop: StopCB | None = None,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.mapfile = mapfile
        self.cfg = config or RescueConfig()
        self.mapfile_path = mapfile_path
        self.on_progress = on_progress
        self.should_stop = should_stop or (lambda: False)
        self.stats = Stats()
        self._last_sync = 0.0
        self._last_report = 0.0
        self._rate_window: tuple[float, int] = (time.monotonic(), 0)
        self._report_window: tuple[float, int] = (time.monotonic(), 0)
        self._stopped = False

    # ------------------------------------------------------------------ public
    @property
    def map(self) -> ExtentMap:
        return self.mapfile.extents

    def run(self) -> Stats:
        """Execute every enabled phase until done, aborted or interrupted."""
        self.stats.start_time = time.monotonic()
        try:
            self._copy_phases()
            if self.cfg.trim:
                self._run_phase("trim", 1, self._trim_pass)
            if self.cfg.scrape:
                self._run_phase("scrape", 1, self._scrape_pass)
            self._retry_phases()
        except _Aborted:
            pass
        finally:
            self._refresh_stats()
            self.mapfile.current_status = "+" if self.map.is_done(self.cfg.domain) else self.stats_status()
            self._checkpoint(force=True)
        return self.stats

    def stats_status(self) -> str:
        return {"copy": NON_TRIED, "trim": NON_TRIMMED, "scrape": NON_SCRAPED,
                "retry": BAD}.get(self.stats.phase, NON_TRIED)

    # ------------------------------------------------------------------ phases
    def _copy_phases(self) -> None:
        for n in range(1, max(1, self.cfg.copy_passes) + 1):
            if not self._has(NON_TRIED):
                return
            # Alternate direction: a backwards pass picks up the areas that the
            # forward pass skipped over, approaching them from the healthy side.
            reverse = self.cfg.reverse if n % 2 == 1 else not self.cfg.reverse
            # The last pass reads everything left, without skipping.
            skipping = n < max(1, self.cfg.copy_passes)
            self._run_phase("copy", n, lambda: self._copy_pass(reverse, skipping))

    def _retry_phases(self) -> None:
        n = 0
        while self.cfg.retries < 0 or n < self.cfg.retries:
            n += 1
            if not self._has(BAD):
                return
            reverse = (n % 2 == 0) != self.cfg.reverse
            self._run_phase("retry", n, lambda: self._retry_pass(reverse))

    def _run_phase(self, name: str, pass_no: int, body: Callable[[], None]) -> None:
        self.stats.phase = name
        self.stats.pass_no = pass_no
        self.mapfile.current_status = self.stats_status()
        self.mapfile.current_pass = pass_no
        self._report(force=True)
        body()
        self._checkpoint(force=True)

    # ------------------------------------------------------------ copy phase
    def _copy_pass(self, reverse: bool, skipping: bool) -> None:
        cluster = self.cfg.cluster_bytes
        skip = 0
        for pos, size in self._areas(NON_TRIED, reverse):
            end = pos + size
            cursor = end if reverse else pos
            while (cursor > pos) if reverse else (cursor < end):
                self._tick()
                if reverse:
                    chunk_end, chunk_pos = cursor, max(pos, cursor - cluster)
                else:
                    chunk_pos, chunk_end = cursor, min(end, cursor + cluster)
                if chunk_end <= chunk_pos:
                    break
                if self._try_read(chunk_pos, chunk_end - chunk_pos, on_fail=NON_TRIMMED):
                    skip = 0
                    cursor = chunk_pos if reverse else chunk_end
                    continue
                if not skipping:
                    cursor = chunk_pos if reverse else chunk_end
                    continue
                # Run away from the damaged region, doubling the jump each time.
                skip = min(self.cfg.max_skip_size, skip * 2 if skip else self.cfg.skip_size)
                cursor = chunk_pos - skip if reverse else chunk_end + skip

    # ------------------------------------------------------------ trim phase
    def _trim_pass(self) -> None:
        ss = self.cfg.sector_size
        for pos, size in self._areas(NON_TRIMMED, self.cfg.reverse):
            end = pos + size
            # Forward edge.
            cur = pos
            while cur < end:
                self._tick()
                n = min(ss, end - cur)
                if not self._try_read(cur, n, on_fail=None):
                    break
                cur += n
            if cur >= end:
                continue
            head = cur
            # Backward edge.
            cur = end
            while cur > head:
                self._tick()
                n = min(ss, cur - head)
                if not self._try_read(cur - n, n, on_fail=None):
                    break
                cur -= n
            if cur > head:
                self.map.set_status(head, cur - head, NON_SCRAPED)

    # ---------------------------------------------------------- scrape phase
    def _scrape_pass(self) -> None:
        ss = self.cfg.sector_size
        for pos, size in self._areas(NON_SCRAPED, self.cfg.reverse):
            for sec_pos, n in _sectors(pos, size, ss, self.cfg.reverse):
                self._tick()
                self._try_read(sec_pos, n, on_fail=BAD)

    # ----------------------------------------------------------- retry phase
    def _retry_pass(self, reverse: bool) -> None:
        ss = self.cfg.sector_size
        for pos, size in self._areas(BAD, reverse):
            for sec_pos, n in _sectors(pos, size, ss, reverse):
                self._tick()
                self._try_read(sec_pos, n, on_fail=None, drop_cache=True)

    # ----------------------------------------------------------------- I/O
    def _try_read(self, pos: int, size: int, *, on_fail: str | None,
                  drop_cache: bool = False) -> bool:
        """Read, write through to the image, and record the outcome in the map."""
        if drop_cache:
            dc = getattr(self.reader, "drop_cache", None)
            if dc is not None:
                dc(pos, size)
        try:
            data = self.reader.pread(pos, size)
        except (DeviceReadError, OSError):
            self.stats.errors += 1
            if on_fail is not None:
                self.map.set_status(pos, size, on_fail)
            if self.cfg.fill_bad is not None and self.writer is not None:
                self.writer.pwrite(pos, bytes([self.cfg.fill_bad]) * size)
            self._check_limits()
            return False
        if not data:
            # Past the end of the medium: nothing left to rescue here.
            self.map.set_status(pos, size, FINISHED)
            return True
        if self.writer is not None:
            self.writer.pwrite(pos, data)
        self.map.set_status(pos, len(data), FINISHED)
        self.stats.read_bytes += len(data)
        self.stats.current_pos = pos + len(data)
        # A short read marks only what actually arrived: the tail keeps its
        # current status and is picked up by a later phase.
        return True

    def _check_limits(self) -> None:
        cfg = self.cfg
        if cfg.max_errors is not None and self.stats.errors >= cfg.max_errors:
            raise _Aborted(f"error limit reached ({self.stats.errors})")
        if cfg.max_bad_bytes is not None:
            if self.map.bytes_with(BAD, NON_TRIMMED, NON_SCRAPED) >= cfg.max_bad_bytes:
                raise _Aborted("bad-byte limit reached")

    # -------------------------------------------------------------- plumbing
    def _areas(self, status: str, reverse: bool) -> Iterator[Range]:
        """Snapshot of the ranges with ``status`` (the map mutates while we read)."""
        areas = list(self.map.ranges(status, domain=self.cfg.domain))
        if reverse:
            areas.reverse()
        return iter(areas)

    def _has(self, status: str) -> bool:
        return self.map.bytes_with(status, domain=self.cfg.domain) > 0

    def _tick(self) -> None:
        if self.should_stop():
            raise _Aborted("interrupted")
        self._throttle()
        now = time.monotonic()
        if now - self._last_report >= 0.25:
            self._report()
        if self.cfg.sync_interval and now - self._last_sync >= self.cfg.sync_interval:
            self._checkpoint()

    def _throttle(self) -> None:
        limit = self.cfg.rate_limit
        if not limit:
            return
        t0, b0 = self._rate_window
        elapsed = time.monotonic() - t0
        moved = self.stats.read_bytes - b0
        if elapsed >= 1.0:
            self._rate_window = (time.monotonic(), self.stats.read_bytes)
            return
        allowed = limit * max(elapsed, 1e-9)
        if moved > allowed:
            time.sleep(min(1.0, (moved - allowed) / limit))

    def _refresh_stats(self) -> None:
        totals = self.map.totals(self.cfg.domain)
        s = self.stats
        s.rescued = totals[FINISHED]
        s.non_tried = totals[NON_TRIED]
        s.non_trimmed = totals[NON_TRIMMED]
        s.non_scraped = totals[NON_SCRAPED]
        s.bad = totals[BAD]
        s.bad_areas = sum(1 for _ in self.map.ranges(BAD, domain=self.cfg.domain))
        s.run_time = time.monotonic() - s.start_time

    def _report(self, force: bool = False) -> None:
        now = time.monotonic()
        self._last_report = now
        self._refresh_stats()
        t0, b0 = self._report_window
        span = now - t0
        if span >= 0.5 or force:
            if span > 0:
                self.stats.current_rate = (self.stats.read_bytes - b0) / span
            self._report_window = (now, self.stats.read_bytes)
        if self.on_progress is not None:
            self.on_progress(self.stats)

    def _checkpoint(self, force: bool = False) -> None:
        self._last_sync = time.monotonic()
        self.mapfile.current_pos = self.stats.current_pos
        if self.mapfile_path:
            self.mapfile.save(self.mapfile_path)
        if force and self.writer is not None:
            self.writer.flush()


class _Aborted(Exception):
    """Internal signal: stop the run but save state cleanly."""


def _sectors(pos: int, size: int, sector: int, reverse: bool) -> Iterator[Range]:
    """Split ``[pos, pos+size)`` into sector-aligned reads."""
    end = pos + size
    bounds = []
    cur = pos
    while cur < end:
        nxt = min(end, align_up(cur + 1, sector))
        bounds.append((cur, nxt - cur))
        cur = nxt
    if reverse:
        bounds.reverse()
    return iter(bounds)
