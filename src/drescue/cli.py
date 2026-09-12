"""Command line interface.

    drescue rescue SOURCE DEST [MAPFILE]   fault-tolerant imaging
    drescue status MAPFILE                 what a previous run achieved
    drescue scan   TARGET                  partitions + filesystems (+ lost ones)
    drescue carve  TARGET -o DIR           signature-based file recovery
    drescue verify SOURCE IMAGE [MAPFILE]  prove the image matches the medium

Exit codes: 0 = complete, 1 = finished with unreadable areas left,
2 = interrupted, 3 = usage/environment error.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import stat
import sys
from dataclasses import asdict
from typing import Sequence

from . import __version__
from .device import BlockReader, BlockWriter
from .extents import BAD, FINISHED, NON_SCRAPED, NON_TRIED, NON_TRIMMED, ExtentMap, Range
from .mapfile import Mapfile, MapfileError
from .rescue import Rescuer, RescueConfig
from .reporting import (
    StatusPrinter,
    human_bytes,
    human_time,
    map_legend,
    render_map,
    summary_lines,
    color_enabled,
)
from .scan import find_lost_filesystems, identify_filesystem, read_partitions
from .scan.carver import CarveConfig, carve

EXIT_OK, EXIT_INCOMPLETE, EXIT_INTERRUPTED, EXIT_USAGE = 0, 1, 2, 3

_SUFFIXES = {
    "b": 1, "s": 512,
    "k": 1000, "m": 1000**2, "g": 1000**3, "t": 1000**4, "p": 1000**5,
    "ki": 1024, "mi": 1024**2, "gi": 1024**3, "ti": 1024**4, "pi": 1024**5,
}


def parse_size(text: str) -> int:
    """``"4MiB"`` → 4194304, ``"4MB"`` → 4000000, ``"0x200"`` → 512."""
    s = text.strip().replace("_", "")
    if not s:
        raise argparse.ArgumentTypeError("empty size")
    if s.lower().startswith(("0x", "0o", "0b")):
        return int(s, 0)
    num = s.rstrip("BbKkMmGgTtPpIiSs")
    suffix = s[len(num) :].lower().rstrip("b")
    if not num:
        raise argparse.ArgumentTypeError(f"bad size {text!r}")
    try:
        value = float(num)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"bad size {text!r}") from exc
    mult = _SUFFIXES.get(suffix, 1) if suffix else 1
    if suffix and suffix not in _SUFFIXES:
        raise argparse.ArgumentTypeError(f"unknown size suffix in {text!r}")
    return int(value * mult)


def parse_domain(text: str) -> Range:
    """``"1MiB:4MiB"`` (pos:size) or ``"1MiB-5MiB"`` (pos-end)."""
    if ":" in text:
        a, b = text.split(":", 1)
        return parse_size(a), parse_size(b)
    if "-" in text[1:]:
        i = text.index("-", 1)
        a, b = text[:i], text[i + 1 :]
        pos, end = parse_size(a), parse_size(b)
        if end <= pos:
            raise argparse.ArgumentTypeError(f"empty domain {text!r}")
        return pos, end - pos
    raise argparse.ArgumentTypeError(f"domain must be POS:SIZE or POS-END, got {text!r}")


# --------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="drescue",
        description="Block-level data recovery: imaging, structure scan and carving.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Sizes accept suffixes: 512, 64KiB, 4MB, 1Gi, 0x1000, 2048s (sectors).\n"
            "The mapfile format is interchangeable with GNU ddrescue."
        ),
    )
    p.add_argument("--version", action="version", version=f"drescue {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # ------------------------------------------------------------- rescue
    r = sub.add_parser("rescue", help="copy a failing device to an image, bad blocks last")
    r.add_argument("source")
    r.add_argument("dest")
    r.add_argument("mapfile", nargs="?", help="resume/record file (strongly recommended)")
    r.add_argument("-s", "--size", type=parse_size, help="bytes to copy (default: whole device)")
    r.add_argument("-i", "--input-position", type=parse_size, default=0)
    r.add_argument("-b", "--sector-size", type=parse_size, default=None,
                   help="device sector size (default: probed, else 512)")
    r.add_argument("-c", "--cluster-size", type=int, default=128,
                   help="sectors per read in the copy phase (default: 128)")
    r.add_argument("-K", "--skip-size", type=parse_size, default=parse_size("64KiB"),
                   help="initial jump after a read error (0 disables skipping)")
    r.add_argument("--max-skip-size", type=parse_size, default=parse_size("16MiB"))
    r.add_argument("-p", "--passes", type=int, default=3, help="copy passes (default: 3)")
    r.add_argument("-r", "--retries", type=int, default=1,
                   help="retry passes over bad sectors, -1 for unlimited")
    r.add_argument("-N", "--no-trim", action="store_true")
    r.add_argument("-n", "--no-scrape", action="store_true")
    r.add_argument("-R", "--reverse", action="store_true", help="start from the end")
    r.add_argument("-e", "--max-errors", type=int, default=None)
    r.add_argument("--max-bad-bytes", type=parse_size, default=None)
    r.add_argument("--rate-limit", type=parse_size, default=None, help="bytes per second")
    r.add_argument("-d", "--direct", action="store_true",
                   help="O_DIRECT reads: bypass the page cache so retries hit the medium")
    r.add_argument("--domain", action="append", type=parse_domain, metavar="POS:SIZE",
                   help="restrict work to this range (repeatable)")
    r.add_argument("--domain-partition", type=int, metavar="N",
                   help="restrict work to partition N of the source")
    r.add_argument("--fill-bad", type=lambda v: int(v, 0), metavar="BYTE",
                   help="write this byte over unreadable areas instead of leaving them")
    r.add_argument("--sync-interval", type=float, default=30.0,
                   help="seconds between mapfile checkpoints (default: 30)")
    r.add_argument("-f", "--force", action="store_true",
                   help="allow writing onto an existing block device")
    r.add_argument("-q", "--quiet", action="store_true")
    r.add_argument("--json", action="store_true", help="machine-readable final report")

    # ------------------------------------------------------------- status
    s = sub.add_parser("status", help="summarise a mapfile")
    s.add_argument("mapfile")
    s.add_argument("--width", type=int, default=64, help="map visualisation width")
    s.add_argument("--list", action="store_true", help="list every non-finished area")
    s.add_argument("--json", action="store_true")

    # --------------------------------------------------------------- scan
    sc = sub.add_parser("scan", help="partition table, filesystems and lost volumes")
    sc.add_argument("target", help="device or image file")
    sc.add_argument("-b", "--sector-size", type=parse_size, default=None)
    sc.add_argument("--deep", action="store_true",
                    help="sweep the whole medium for filesystems with no partition entry")
    sc.add_argument("--json", action="store_true")

    # -------------------------------------------------------------- carve
    c = sub.add_parser("carve", help="recover files by signature, flagging damaged ones")
    c.add_argument("target")
    c.add_argument("-o", "--outdir", help="destination directory (omit for a dry run)")
    c.add_argument("-m", "--mapfile", help="rescue mapfile: flags files that hit holes")
    c.add_argument("-t", "--types", help="comma-separated extensions to look for")
    c.add_argument("--align", type=parse_size, default=512,
                   help="header alignment: cluster size (default 512, use 1 for embedded data)")
    c.add_argument("--start", type=parse_size, default=0)
    c.add_argument("--end", type=parse_size, default=None)
    c.add_argument("--max-files", type=int, default=None)
    c.add_argument("--skip-suspect", action="store_true",
                   help="discard files that overlap unrescued sectors")
    c.add_argument("--allow-nested", action="store_true",
                   help="also carve files found inside other files")
    c.add_argument("--json", action="store_true")

    # ------------------------------------------------------------- verify
    v = sub.add_parser("verify", help="re-read the source and compare it to the image")
    v.add_argument("source")
    v.add_argument("image")
    v.add_argument("mapfile", nargs="?")
    v.add_argument("-b", "--sector-size", type=parse_size, default=None)
    v.add_argument("-d", "--direct", action="store_true")
    v.add_argument("--json", action="store_true")
    return p


# -------------------------------------------------------------------- helpers
def _resolve_domain(args, reader, size: int, start: int) -> list[Range] | None:
    domain: list[Range] = list(getattr(args, "domain", None) or [])
    part_no = getattr(args, "domain_partition", None)
    if part_no:
        table = read_partitions(reader, getattr(args, "sector_size", None))
        match = next((p for p in table if p.index == part_no), None)
        if match is None:
            raise SystemExit(f"drescue: partition {part_no} not found on {reader.path}")
        domain.append((match.start, match.size))
    if not domain:
        return None
    clipped = [
        (max(p, start), min(p + s, start + size) - max(p, start))
        for p, s in domain
    ]
    return [(p, s) for p, s in clipped if s > 0]


def _check_destination(source: str, dest: str, force: bool) -> None:
    if os.path.exists(dest) and os.path.samefile(source, dest):
        raise SystemExit("drescue: source and destination are the same object")
    try:
        st = os.stat(dest)
    except FileNotFoundError:
        return
    if stat.S_ISBLK(st.st_mode) and not force:
        raise SystemExit(
            f"drescue: {dest} is a block device; refusing to overwrite it without --force"
        )


# ------------------------------------------------------------------- commands
def cmd_rescue(args) -> int:
    reader = BlockReader(args.source, direct=args.direct, sector_size=args.sector_size)
    try:
        start = args.input_position
        size = args.size if args.size is not None else max(0, reader.size - start)
        if size <= 0:
            raise SystemExit("drescue: nothing to copy (size is 0)")
        _check_destination(args.source, args.dest, args.force)
        domain = _resolve_domain(args, reader, size, start)

        cfg = RescueConfig(
            sector_size=args.sector_size or reader.sector_size,
            cluster_size=args.cluster_size,
            skip_size=args.skip_size,
            max_skip_size=args.max_skip_size,
            reverse=args.reverse,
            copy_passes=args.passes,
            trim=not args.no_trim,
            scrape=not args.no_scrape,
            retries=args.retries,
            max_errors=args.max_errors,
            max_bad_bytes=args.max_bad_bytes,
            rate_limit=args.rate_limit,
            sync_interval=args.sync_interval,
            domain=domain,
            fill_bad=args.fill_bad,
        )
        command_line = "drescue " + " ".join(sys.argv[1:])
        if args.mapfile:
            mapfile = Mapfile.load_or_create(args.mapfile, start, size, command_line)
        else:
            # No mapfile: the run is neither resumable nor recorded.
            mapfile = Mapfile(extents=ExtentMap.covering(start, size),
                              current_pos=start, command_line=command_line)

        stop = _InterruptFlag()
        printer = None if args.quiet else StatusPrinter(sys.stderr, size=size)
        if printer is not None:
            print(
                f"drescue {__version__}: {args.source} -> {args.dest} "
                f"({human_bytes(size)}, sector {cfg.sector_size} B"
                f"{', O_DIRECT' if reader.direct else ''})",
                file=sys.stderr,
            )

        with BlockWriter(args.dest, size=start + size) as writer:
            rescuer = Rescuer(
                reader, writer, mapfile, cfg,
                mapfile_path=args.mapfile,
                on_progress=(
                    (lambda st: printer.update(st, mapfile.extents, domain))
                    if printer else None
                ),
                should_stop=stop,
            )
            with stop.installed():
                stats = rescuer.run()
        if printer is not None:
            printer.finish()

        emap = mapfile.extents
        if args.json:
            print(json.dumps(_rescue_report(args, stats, emap, domain), indent=2))
        elif not args.quiet:
            print("\n".join(summary_lines(emap, domain)))
            if stop.triggered:
                print("interrupted — rerun the same command to resume", file=sys.stderr)
        if stop.triggered:
            return EXIT_INTERRUPTED
        return EXIT_OK if emap.is_done(domain) else EXIT_INCOMPLETE
    finally:
        reader.close()


def _rescue_report(args, stats, emap: ExtentMap, domain) -> dict:
    totals = emap.totals(domain)
    return {
        "source": args.source,
        "dest": args.dest,
        "mapfile": args.mapfile,
        "bytes": {k: v for k, v in totals.items()},
        "rescued": totals[FINISHED],
        "unreadable": totals[BAD] + totals[NON_TRIMMED] + totals[NON_SCRAPED],
        "bad_areas": stats.bad_areas,
        "read_errors": stats.errors,
        "run_time_seconds": round(stats.run_time, 3),
        "average_rate": round(stats.average_rate, 1),
        "complete": emap.is_done(domain),
        "bad_ranges": [
            {"offset": p, "size": s}
            for p, s in emap.ranges(BAD, NON_TRIMMED, NON_SCRAPED, domain=domain)
        ][:1000],
    }


def cmd_status(args) -> int:
    try:
        mf = Mapfile.load(args.mapfile)
    except (OSError, MapfileError) as exc:
        raise SystemExit(f"drescue: {exc}")
    emap = mf.extents
    if args.json:
        print(json.dumps({
            "mapfile": args.mapfile,
            "current_pos": mf.current_pos,
            "current_status": mf.current_status,
            "current_pass": mf.current_pass,
            "size": emap.size,
            "bytes": emap.totals(),
            "complete": emap.is_done(),
            "areas": [
                {"offset": e.pos, "size": e.size, "status": e.status}
                for e in emap if e.status != FINISHED
            ][:10000],
        }, indent=2))
        return EXIT_OK if emap.is_done() else EXIT_INCOMPLETE
    color = color_enabled(sys.stdout)
    print(f"mapfile: {args.mapfile}")
    print(f"covers:  0x{emap.start:x} .. 0x{emap.end:x}  ({human_bytes(emap.size)})")
    print(f"state:   {mf.current_status!r} pass {mf.current_pass} at 0x{mf.current_pos:x}")
    print()
    print("\n".join(summary_lines(emap)))
    print()
    print("  " + render_map(emap, args.width, color=color))
    print("  " + map_legend(color))
    if args.list:
        print("\nunfinished areas:")
        for e in emap:
            if e.status != FINISHED:
                print(f"  0x{e.pos:012x}  {human_bytes(e.size):>10}  {e.status}")
    return EXIT_OK if emap.is_done() else EXIT_INCOMPLETE


def cmd_scan(args) -> int:
    reader = BlockReader(args.target, sector_size=args.sector_size)
    try:
        table = read_partitions(reader, args.sector_size)
        known: list[Range] = []
        rows = []
        for part in table:
            fs = identify_filesystem(reader, part.start)
            part.filesystem = fs
            known.append((part.start, part.size))
            rows.append((part, fs))
        whole_fs = identify_filesystem(reader, 0) if not rows else None
        lost = []
        if args.deep:
            # Suppress only the volumes already accounted for, never whole spans.
            covered = list(known) + ([(0, 1)] if whole_fs is not None else [])
            lost = list(find_lost_filesystems(
                reader, sector_size=args.sector_size or reader.sector_size,
                known=covered,
            ))

        if args.json:
            print(json.dumps({
                "target": args.target,
                "size": reader.size,
                "sector_size": args.sector_size or reader.sector_size,
                "scheme": table.scheme,
                "disk_guid": table.disk_guid,
                "notes": table.notes,
                "filesystem": _fs_json(whole_fs),
                "partitions": [
                    {
                        "index": p.index, "start": p.start, "size": p.size,
                        "type": p.kind, "type_id": p.type_id, "name": p.name,
                        "guid": p.guid, "bootable": p.bootable,
                        "filesystem": _fs_json(fs),
                    }
                    for p, fs in rows
                ],
                "lost_filesystems": [_fs_json(f) for f in lost],
            }, indent=2))
            return EXIT_OK

        print(f"target:      {args.target}")
        print(f"size:        {human_bytes(reader.size)} ({reader.size} bytes)")
        print(f"sector size: {args.sector_size or reader.sector_size}")
        print(f"scheme:      {table.scheme}")
        if table.disk_guid:
            print(f"disk GUID:   {table.disk_guid}")
        for note in table.notes:
            print(f"  ! {note}")
        if whole_fs is not None:
            print(f"\nunpartitioned volume: {whole_fs.describe()}")
        if rows:
            print(f"\n{'#':>3}  {'start':>14}  {'size':>12}  {'type':<24} filesystem")
            for p, fs in rows:
                print(
                    f"{p.index:>3}  {p.start:>14}  {human_bytes(p.size):>12}  "
                    f"{p.kind[:24]:<24} {fs.describe() if fs else '-'}"
                    + (f"  [{p.name}]" if p.name else "")
                )
        if args.deep:
            print(f"\nlost/unreferenced filesystems: {len(lost)}")
            for fs in lost:
                print(f"  0x{fs.offset:012x}  {fs.describe()}")
        elif not rows and whole_fs is None:
            print("\nno partition table and no filesystem at offset 0 — try --deep")
        return EXIT_OK
    finally:
        reader.close()


def _fs_json(fs) -> dict | None:
    if fs is None:
        return None
    return {
        "kind": fs.kind, "offset": fs.offset, "label": fs.label, "uuid": fs.uuid,
        "block_size": fs.block_size, "size": fs.size, "details": fs.details,
    }


def cmd_carve(args) -> int:
    reader = BlockReader(args.target)
    try:
        rescued = None
        if args.mapfile:
            rescued = Mapfile.load(args.mapfile).extents
        cfg = CarveConfig(
            alignment=max(1, args.align),
            skip_nested=not args.allow_nested,
            skip_suspect=args.skip_suspect,
            max_files=args.max_files,
            extensions=[t.strip() for t in args.types.split(",")] if args.types else None,
        )
        found = []
        suspects = 0
        for item in carve(reader, args.outdir, config=cfg, rescued=rescued,
                          start=args.start, end=args.end):
            found.append(item)
            suspects += bool(item.suspect)
            if not args.json:
                flag = f"  SUSPECT ({human_bytes(item.hole_bytes)} unrescued)" if item.suspect else ""
                print(f"0x{item.offset:012x}  {human_bytes(item.size):>10}  "
                      f"{item.ext:<6} {item.name}{flag}")
        if args.json:
            print(json.dumps({
                "target": args.target,
                "outdir": args.outdir,
                "count": len(found),
                "suspect": suspects,
                "files": [
                    {
                        "offset": f.offset, "size": f.size, "ext": f.ext,
                        "path": f.path, "hole_bytes": f.hole_bytes,
                        "integrity": round(f.integrity, 6), "suspect": f.suspect,
                    }
                    for f in found
                ],
            }, indent=2))
        else:
            total = sum(f.size for f in found)
            print(f"\n{len(found)} file(s), {human_bytes(total)}"
                  + (f", {suspects} suspect" if suspects else "")
                  + (" (dry run, nothing written)" if not args.outdir else ""))
        return EXIT_OK
    finally:
        reader.close()


def cmd_verify(args) -> int:
    import hashlib

    src = BlockReader(args.source, direct=args.direct, sector_size=args.sector_size)
    img = BlockReader(args.image)
    try:
        if args.mapfile:
            ranges = list(Mapfile.load(args.mapfile).extents.ranges(FINISHED))
        else:
            ranges = [(0, min(src.size, img.size))]
        h_src, h_img = hashlib.sha256(), hashlib.sha256()
        checked = mismatched = unreadable = 0
        bad_ranges: list[dict] = []
        for pos, size in ranges:
            cursor = pos
            while cursor < pos + size:
                n = min(1 << 20, pos + size - cursor)
                try:
                    a = src.pread(cursor, n)
                except OSError:
                    unreadable += n
                    cursor += n
                    continue
                b = img.pread(cursor, n)
                h_src.update(a)
                h_img.update(b)
                checked += len(a)
                if a != b:
                    mismatched += len(a)
                    bad_ranges.append({"offset": cursor, "size": len(a)})
                cursor += n
        ok = mismatched == 0 and unreadable == 0
        if args.json:
            print(json.dumps({
                "source": args.source, "image": args.image,
                "checked": checked, "mismatched": mismatched,
                "unreadable": unreadable, "match": ok,
                "sha256_source": h_src.hexdigest(), "sha256_image": h_img.hexdigest(),
                "mismatched_ranges": bad_ranges[:1000],
            }, indent=2))
        else:
            print(f"checked:     {human_bytes(checked)}")
            print(f"mismatched:  {human_bytes(mismatched)}")
            print(f"unreadable:  {human_bytes(unreadable)}")
            print(f"sha256 src:  {h_src.hexdigest()}")
            print(f"sha256 img:  {h_img.hexdigest()}")
            print("result:      " + ("MATCH" if ok else "DIFFERENT"))
        return EXIT_OK if ok else EXIT_INCOMPLETE
    finally:
        src.close()
        img.close()


class _InterruptFlag:
    """First Ctrl-C stops cleanly (mapfile saved); a second one kills the process."""

    def __init__(self) -> None:
        self.triggered = False
        self._previous = None

    def __call__(self) -> bool:
        return self.triggered

    def installed(self):
        flag = self

        class _Ctx:
            def __enter__(self_inner):
                try:
                    flag._previous = signal.signal(signal.SIGINT, flag._handle)
                except ValueError:  # not the main thread
                    flag._previous = None
                return flag

            def __exit__(self_inner, *exc):
                if flag._previous is not None:
                    signal.signal(signal.SIGINT, flag._previous)
                return False

        return _Ctx()

    def _handle(self, signum, frame) -> None:
        if self.triggered:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            raise KeyboardInterrupt
        self.triggered = True
        print("\ninterrupt: finishing the current read and saving the mapfile "
              "(Ctrl-C again to abort now)", file=sys.stderr)


COMMANDS = {
    "rescue": cmd_rescue,
    "status": cmd_status,
    "scan": cmd_scan,
    "carve": cmd_carve,
    "verify": cmd_verify,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            return EXIT_USAGE
        return int(exc.code or 0)
    except KeyboardInterrupt:
        print("\naborted", file=sys.stderr)
        return EXIT_INTERRUPTED
    except (OSError, MapfileError, ValueError) as exc:
        print(f"drescue: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
