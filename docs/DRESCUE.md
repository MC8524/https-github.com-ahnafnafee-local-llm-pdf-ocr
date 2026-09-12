# drescue

Block-level data recovery: fault-tolerant imaging, structure scanning and file
carving, in one dependency-free Python tool.

```
drescue rescue SOURCE DEST [MAPFILE]   image a failing device, bad blocks last
drescue status MAPFILE                 what a previous run achieved
drescue scan   TARGET                  partitions + filesystems (+ lost ones)
drescue carve  TARGET -o DIR           recover files by signature
drescue verify SOURCE IMAGE [MAPFILE]  prove the image matches the medium
```

Run it with `python drescue_cli.py <command>` (or `uv run drescue_cli.py ...`).
It imports nothing outside the standard library, so it works from a rescue USB
stick where `pip install` is not an option.

## Honest positioning

This was written to cover what GNU ddrescue and DMDE do for the common case.
It does **not** replace either of them, and here is exactly where the line is.

| | drescue | GNU ddrescue | DMDE |
|---|---|---|---|
| Fault-tolerant imaging (copy/trim/scrape/retry) | yes | yes, the original | yes |
| ddrescue-compatible mapfile | yes, read *and* write | yes | no |
| Resume across interruption/power loss | yes | yes | yes |
| `O_DIRECT` reads so retries reach the medium | yes | yes | yes |
| Partition table parsing (MBR/GPT + backup GPT) | yes | no | yes, far deeper |
| Filesystem identification | 19 signatures | no | dozens, with full parsers |
| Lost-partition sweep | signature level | no | signature **and** metadata level |
| File carving | 25 signatures, exact lengths | no | yes |
| Carving that knows which sectors were rescued | **yes** | n/a | no |
| Browsing/undeleting files from NTFS/ext/FAT directory trees | **no** | no | yes, its core strength |
| RAID reconstruction, virtual disks, disk editor, GUI | **no** | no | yes |
| Years of field-hardening against real dying drives | **no** | ~20 | ~15 |

Two honest summaries:

* Against **ddrescue**: the imaging algorithm is a faithful reimplementation of
  the same strategy, the mapfiles are interchangeable in both directions, and
  the scan/carve/verify commands are additions ddrescue does not have. ddrescue
  is still C, decades older, and will be faster on a large healthy disk —
  Python's per-read overhead is real (see *Performance* below).
* Against **DMDE**: not close on filesystem knowledge. DMDE reads NTFS MFT
  records and ext inode tables and hands you a file tree; drescue only
  identifies volumes and carves by signature. If you need to undelete a named
  file from a healthy NTFS volume, use DMDE.

The one thing here that neither tool does: **carving that reads the rescue
mapfile**. After a rescue, the holes the drive refused to give up are zeros in
the image and look like perfectly good file content to any ordinary carver.
`drescue carve -m disk.map` reports, per extracted file, how many bytes came out
of unreadable areas — so a photo that is 3 % hole is flagged instead of silently
shipped as "recovered".

## Imaging

```bash
# The normal case: image a dying disk, keep a mapfile, bypass the page cache.
drescue rescue /dev/sdb disk.img disk.map --direct

# Interrupt with Ctrl-C at any time; the same command resumes where it stopped.
drescue rescue /dev/sdb disk.img disk.map --direct

# Only the partition that matters — do not spend the drive's remaining life
# on the 900 GB of free space.
drescue rescue /dev/sdb part2.img part2.map --domain-partition 2

# Triage first: grab everything easy, give up quickly on damage.
drescue rescue /dev/sdb disk.img disk.map --no-trim --no-scrape -r 0

# Then come back for the hard parts, slowly and from the other end.
drescue rescue /dev/sdb disk.img disk.map -r 5 --reverse
```

### The algorithm

A dying drive has a budget: every read of a bad sector costs seconds of head
thrashing and brings the next failure closer. So the work is ordered to get the
healthy 99 % off first and only then negotiate for the rest.

1. **copy** — read in 64 KiB clusters; on the first error, mark the cluster
   `non-trimmed` and *jump ahead* (64 KiB, doubling while errors continue).
   Passes alternate direction so a damaged region is also approached from its
   healthy side.
2. **trim** — nibble at each failed cluster from both edges in sector steps;
   what survives in the middle becomes `non-scraped`.
3. **scrape** — read those middles sector by sector; what fails is genuinely
   `bad-sector`.
4. **retry** — re-read only bad sectors, alternating direction, cache dropped
   before each attempt. Marginal sectors often come back on attempt three.

Every transition is checkpointed to the mapfile (every 30 s by default, and at
every phase boundary), so an interrupted run — including a power cut — resumes
without re-reading a single finished byte.

### Mapfile compatibility

The mapfile is GNU ddrescue's format, byte for byte, with the same status
alphabet (`?` non-tried, `*` non-trimmed, `/` non-scraped, `-` bad-sector,
`+` finished). A mapfile from `ddrescue` can be continued by `drescue` and vice
versa. `tests/drescue/test_mapfile.py` parses a verbatim ddrescue 1.27 mapfile
as a regression test.

```bash
drescue status disk.map --list
```

```
mapfile: disk.map
covers:  0x0 .. 0x3a3812ab000  (4.0 TB)
state:   '-' pass 2 at 0x1c2f4000

     non-tried:       0 B    0.00%  (0 areas)
   non-trimmed:       0 B    0.00%  (0 areas)
   non-scraped:       0 B    0.00%  (0 areas)
    bad-sector:   131.1 kB    0.00%  (17 areas)
      finished:     4.0 TB   99.99%  (18 areas)

  ###############################X######################X#########
  # finished   . non-tried   * non-trimmed   / non-scraped   X bad-sector
```

Each cell of the map shows the **worst** status in its slice, so one bad sector
in a gigabyte is never hidden behind a green block.

## Scanning

```bash
drescue scan /dev/sdb              # partition table + filesystem per partition
drescue scan disk.img --deep       # + sweep for volumes with no table entry
drescue scan disk.img --json       # machine-readable
```

* MBR (including the extended/EBR chain) and GPT.
* GPT header and entry-array CRC32s are validated; a shredded primary GPT falls
  back to the backup at the end of the disk, and says so.
* `--deep` sweeps the medium for filesystem superblocks with `bytes.find` over
  8 MiB chunks, then confirms every hit with a full superblock parse. Hits
  already covered by the partition table are suppressed, so the output is
  exactly the *lost* volumes. This is the cheap version of DMDE's full scan: it
  finds where volumes start, not what is inside them.

Recognised: ext2/3/4, XFS, btrfs, F2FS, NTFS, exFAT, FAT12/16/32, HFS+/HFSX,
APFS containers, ISO9660, squashfs, Linux swap, LUKS1/2, LVM2 physical volumes.

**Verification status, stated honestly:** ext2/3/4 and FAT32 detection is
cross-checked against `blkid` in the test suite (label, UUID, block size and
total size must all agree). The rest is implemented from documented on-disk
layouts and tested against fixtures built from those same layouts — a
consistency check, not an independent one. Fields that come back implausible
are dropped rather than reported, so a wrong offset shows up as a missing label,
never as a wrong one. If you depend on a label or UUID from one of the
unverified filesystems, confirm it with `blkid` before acting on it.

## Carving

```bash
# Recover files from a rescued image, flagging the ones that hit holes.
drescue carve disk.img -o recovered -m disk.map

# Only photos, and only files that are 100 % rescued.
drescue carve disk.img -o photos -t jpg,png --skip-suspect

# Dry run: what is in there, without writing anything.
drescue carve disk.img --json
```

```
0x000000104000      2.4 MB  jpg    f0000000000104000.jpg
0x000000380000     18.1 MB  mp4    f0000000000380000.mp4  SUSPECT (4.1 kB unrescued)
```

Where the format allows it, the exact file length is computed from the file's
own structure rather than guessed: PNG chunk walk, JPEG marker walk to EOI
(handling byte stuffing and restart markers), GIF block walk, RIFF/BMP/SQLite/
ELF size fields, MP4 box walk, ZIP end-of-central-directory. ZIP and RIFF
containers get their real extension back (`docx`, `xlsx`, `pptx`, `epub`, `jar`,
`wav`, `avi`, `webp`). The test suite carves a real PNG, JPEG, GIF, WAV, DOCX,
SQLite database, BMP and PDF out of an image and asserts every one is recovered
**byte for byte**.

Headers are only accepted on a multiple of `--align` (512 by default, the
cluster/sector boundary a real file starts on); `--align 1` finds embedded data
at the cost of many more false positives. By default a file found inside another
file is skipped (`--allow-nested` turns that off).

## Verifying

```bash
drescue verify /dev/sdb disk.img disk.map
```

Re-reads the source over exactly the areas the mapfile calls `finished`,
compares them against the image byte for byte, and prints a SHA-256 of both
sides. Catches a cable that dropped mid-copy, a destination that ran out of
space, and silent corruption on either end.

## Performance

Python, not C. Copying a healthy 512 MiB file-backed image on the machine this
was developed on:

| cluster | buffered | `--direct` |
|---|---|---|
| `-c 128` (64 KiB, the default) | 127 MB/s | 128 MB/s |
| `-c 512` (256 KiB) | 401 MB/s | 275 MB/s |

At the default cluster the cost is per-read Python overhead, not I/O, so raising
`--cluster-size` is the first thing to try on large healthy media. That is fast
enough for a failing disk — which rarely sustains more than 30 MB/s — and for
images up to a few hundred GB, but ddrescue in C will still win on a healthy
multi-terabyte drive. The scan and carve sweeps run at `bytes.find` speed, which
is C. (Numbers from one VM with file-backed storage; measure your own.)

Two limits worth knowing before you trust it with something irreplaceable:

* The extent map is a plain Python list with binary-search lookup. Measured on
  a 4 TB map: 50 000 separate bad areas (100 000 extents) cost about 8 µs per
  status update and 0.1 s to render the whole-disk visualisation, which the
  live display therefore refreshes only once a second. That is comfortable;
  millions of distinct bad areas would not be.
* Reading a dying drive can hang in the kernel for the duration of the SCSI
  timeout. There is no per-read timeout here — ddrescue's `--timeout` has no
  equivalent yet. Set the kernel timeout yourself if that matters:
  `echo 5 > /sys/block/sdb/device/timeout`.

## Safety

* Never writes to the source. The source is opened `O_RDONLY`.
* Refuses to write onto a block device without `--force`, and refuses outright
  if source and destination are the same object.
* The image file is preallocated sparsely: unreadable areas consume no blocks
  and read back as zeros (use `--fill-bad 0x00` to write an explicit marker
  byte instead).
* First Ctrl-C finishes the current read and saves the mapfile; a second one
  aborts immediately.

Exit codes: `0` complete, `1` finished with unreadable areas left, `2`
interrupted, `3` usage or environment error.

## Layout

```
src/drescue/
  extents.py        interval map: the in-memory mapfile, all phases are
                    "read the areas with status X, rewrite them as Y"
  mapfile.py        ddrescue-format read/write, atomic saves
  device.py         size/sector probing, O_DIRECT aligned reads, sparse writes
  rescue.py         the copy -> trim -> scrape -> retry engine
  reporting.py      live status block, map visualisation, human units
  cli.py            argparse front end for all five commands
  scan/
    partitions.py   MBR + EBR chain, GPT with CRC validation and backup fallback
    filesystems.py  19 superblock probes; identify one, or sweep for lost ones
    carver.py       25 file signatures, exact lengths, mapfile-aware extraction
drescue_cli.py      entry point
tests/drescue/      121 tests
```

## Tests

```bash
uv run pytest tests/drescue -q          # ~7s, no model downloads
```

The rescue engine is tested against an in-memory device with configurable bad
and intermittently-bad sectors, asserting that every good sector lands in the
image byte-exact, that no bad sector is invented, that one bad sector costs one
sector (not one cluster), that a large damaged region is skipped in under ten
reads, that retries recover intermittent sectors, and that interrupting and
resuming produces the same image as an uninterrupted run. Partition parsing is
cross-checked against `partx`, filesystem identification against `blkid`, and
carving against byte-for-byte comparison with the original files. Tests that
need `mkfs.ext4`, `partx` or `blkid` skip cleanly when those are absent.
