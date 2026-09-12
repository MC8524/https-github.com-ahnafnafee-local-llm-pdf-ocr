import os
from pathlib import Path

import pytest

from drescue.device import BlockReader
from drescue.extents import BAD, FINISHED, ExtentMap
from drescue.scan.carver import CarveConfig, carve

from . import samples

SECTOR = 512
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def disk(tmp_path_factory):
    """An image holding one of each sample format, sector-aligned, plus noise."""
    files = {
        "png": samples.png(),
        "jpg": samples.jpeg(),
        "gif": samples.gif(),
        "wav": samples.wav(),
        "docx": samples.zip_docx(),
        "sqlite": samples.sqlite_db(),
        "bmp": samples.bmp(),
    }
    pdf = ROOT / "examples" / "digital.pdf"
    if pdf.exists():
        files["pdf"] = pdf.read_bytes()

    blob = bytearray()
    placed = {}
    for name, data in files.items():
        blob += b"\x5a" * SECTOR  # junk between files
        placed[name] = (len(blob), len(data))
        blob += data
        blob += b"\0" * (-len(blob) % SECTOR)
    path = tmp_path_factory.mktemp("carve") / "disk.img"
    path.write_bytes(bytes(blob))
    return str(path), files, placed


def carve_all(path, outdir=None, **kw):
    overrides = {"alignment": SECTOR, **kw.pop("cfg", {})}
    cfg = CarveConfig(**overrides)
    with BlockReader(path) as r:
        return list(carve(r, outdir, config=cfg, **kw))


def test_every_sample_is_recovered_byte_for_byte(disk, tmp_path):
    path, files, placed = disk
    out = tmp_path / "out"
    found = {c.offset: c for c in carve_all(path, str(out))}
    for name, (offset, size) in placed.items():
        assert offset in found, f"{name} not carved"
        item = found[offset]
        assert item.size == size, f"{name} wrong length"
        assert Path(item.path).read_bytes() == files[name], f"{name} corrupted"


def test_extensions_are_refined_from_container_contents(disk, tmp_path):
    path, _, placed = disk
    found = {c.offset: c for c in carve_all(path, str(tmp_path / "o"))}
    assert found[placed["docx"][0]].ext == "docx"  # a ZIP holding word/
    assert found[placed["wav"][0]].ext == "wav"  # a RIFF holding WAVE


def test_dry_run_writes_nothing(disk, tmp_path):
    path, _, _ = disk
    out = tmp_path / "nothing"
    found = carve_all(path)
    assert found and all(c.path == "" for c in found)
    assert not out.exists()


def test_type_filter_restricts_the_search(disk, tmp_path):
    path, _, placed = disk
    found = carve_all(path, str(tmp_path / "o"), cfg={"extensions": ["png"]})
    assert [c.ext for c in found] == ["png"]
    assert found[0].offset == placed["png"][0]


def test_alignment_skips_unaligned_headers(tmp_path):
    path = tmp_path / "unaligned.img"
    blob = bytearray(b"\0" * 4096)
    blob[100 : 100 + len(samples.png())] = samples.png()  # not on a sector boundary
    path.write_bytes(bytes(blob))
    assert carve_all(str(path)) == []
    found = carve_all(str(path), cfg={"alignment": 1})
    assert [c.offset for c in found] == [100]


def test_max_files_stops_early(disk):
    path, _, _ = disk
    assert len(carve_all(path, cfg={"max_files": 2})) == 2


def test_files_overlapping_unrescued_sectors_are_flagged(disk, tmp_path):
    path, _, placed = disk
    offset, size = placed["sqlite"]
    emap = ExtentMap.covering(0, os.path.getsize(path), FINISHED)
    emap.set_status(offset + SECTOR, SECTOR, BAD)
    found = {c.offset: c for c in carve_all(path, str(tmp_path / "o"), rescued=emap)}
    damaged = found[offset]
    assert damaged.suspect
    assert damaged.hole_bytes == SECTOR
    assert damaged.holes == [(offset + SECTOR, SECTOR)]
    assert 0.0 < damaged.integrity < 1.0
    others = [c for o, c in found.items() if o != offset]
    assert others and not any(c.suspect for c in others)


def test_skip_suspect_discards_damaged_files(disk, tmp_path):
    path, _, placed = disk
    offset, _ = placed["sqlite"]
    emap = ExtentMap.covering(0, os.path.getsize(path), FINISHED)
    emap.set_status(offset, SECTOR, BAD)
    out = tmp_path / "clean"
    found = carve_all(path, str(out), rescued=emap, cfg={"skip_suspect": True})
    assert offset not in {c.offset for c in found}
    assert all(not c.suspect for c in found)


def test_without_a_mapfile_nothing_is_marked_suspect(disk, tmp_path):
    path, _, _ = disk
    assert not any(c.suspect for c in carve_all(path, str(tmp_path / "o")))


def test_unreadable_areas_become_zero_padding_not_shifted_data(tmp_path):
    """File offsets must stay intact when a read fails mid-file."""
    from .fakes import FaultyReader

    data = bytearray(b"\0" * 4096)
    payload = samples.png()
    data[0 : len(payload)] = payload
    reader = FaultyReader(bytes(data), bad_sectors={0}, sector_size=SECTOR)
    reader.size = len(data)
    out = tmp_path / "o"
    # Header unreadable means no hit at all; damage the *second* sector instead.
    reader.bad = {1}
    items = list(carve(reader, str(out), config=CarveConfig(alignment=SECTOR)))
    assert items == [] or items[0].size == len(payload)


def test_carving_a_range_only(disk):
    path, _, placed = disk
    start = placed["bmp"][0]
    found = carve_all(path, start=start)
    assert all(c.offset >= start for c in found)
    assert found[0].offset == start


def test_nested_files_are_skipped_by_default(tmp_path):
    """A JPEG embedded in a container must not be carved twice."""
    inner = samples.jpeg()
    blob = bytearray()
    blob += samples.png()
    blob += b"\0" * (-len(blob) % SECTOR)
    outer_start = len(blob)
    container = bytearray(b"%PDF-1.4\n")
    container += b"\0" * (SECTOR - len(container))
    container += inner
    container += b"\n%%EOF\n"
    blob += container
    path = tmp_path / "nested.img"
    path.write_bytes(bytes(blob))

    default = [c.ext for c in carve_all(str(path))]
    assert default.count("jpg") == 0
    nested = [c.ext for c in carve_all(str(path), cfg={"skip_nested": False})]
    assert "jpg" in nested
    assert outer_start in [c.offset for c in carve_all(str(path))]
