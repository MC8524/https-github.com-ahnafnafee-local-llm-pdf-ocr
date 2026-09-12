import pytest

from drescue.extents import BAD, FINISHED, NON_TRIED, ExtentMap
from drescue.mapfile import Mapfile, MapfileError

# A mapfile exactly as GNU ddrescue writes one.
DDRESCUE_SAMPLE = """\
# Mapfile. Created by GNU ddrescue version 1.27
# Command line: ddrescue -d /dev/sdb disk.img disk.map
# Start time:   2024-01-02 03:04:05
# Current time: 2024-01-02 03:14:05
# copying non-tried blocks... pass 1 (forwards)
#      pos        size  status
0x00001000     ?               1
0x00000000  0x00001000  +
0x00001000  0x00000200  -
0x00001200  0x00002E00  ?
"""


def test_parses_a_real_ddrescue_mapfile():
    mf = Mapfile.parse(DDRESCUE_SAMPLE)
    assert mf.current_pos == 0x1000
    assert mf.current_status == "?"
    assert mf.current_pass == 1
    assert mf.command_line.startswith("ddrescue -d")
    assert mf.extents.totals()[FINISHED] == 0x1000
    assert mf.extents.totals()[BAD] == 0x200
    assert mf.extents.size == 0x4000


def test_round_trips_through_render_and_parse():
    m = ExtentMap.covering(0, 4096)
    m.set_status(1024, 512, BAD)
    original = Mapfile(extents=m, current_pos=1536, current_status="-", current_pass=2)
    reparsed = Mapfile.parse(original.render())
    assert [(e.pos, e.size, e.status) for e in reparsed.extents] == [
        (e.pos, e.size, e.status) for e in original.extents
    ]
    assert reparsed.current_pos == 1536
    assert reparsed.current_status == "-"
    assert reparsed.current_pass == 2


def test_rendered_file_keeps_the_ddrescue_column_layout():
    mf = Mapfile(extents=ExtentMap.covering(0, 512))
    lines = [l for l in mf.render().splitlines() if not l.startswith("#")]
    assert lines[0].split()[:2] == ["0x00000000", "?"]
    assert lines[1].split() == ["0x00000000", "0x00000200", "?"]


def test_save_is_atomic_and_leaves_no_temp_files(tmp_path):
    path = tmp_path / "disk.map"
    Mapfile(extents=ExtentMap.covering(0, 1024)).save(path)
    assert path.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["disk.map"]
    Mapfile.load(path)  # parses back


def test_load_or_create_starts_fresh_when_absent(tmp_path):
    mf = Mapfile.load_or_create(tmp_path / "new.map", 0, 8192, "drescue rescue a b")
    assert mf.extents.totals()[NON_TRIED] == 8192
    assert mf.command_line == "drescue rescue a b"


def test_load_or_create_resumes_and_extends(tmp_path):
    path = tmp_path / "d.map"
    m = ExtentMap.covering(0, 4096)
    m.set_status(0, 2048, FINISHED)
    Mapfile(extents=m).save(path)
    resumed = Mapfile.load_or_create(path, 0, 8192)
    assert resumed.extents.totals()[FINISHED] == 2048
    assert resumed.extents.size == 8192  # grown, prior results kept


@pytest.mark.parametrize(
    "text",
    [
        "0x0 0x10 +\n",  # no status line
        "0x0 ? 1\n0x0 0x10 Z\n",  # unknown block status
        "0x0 ? 1\n0x0 0x10 +\n0x40 0x10 +\n",  # gap
        "",
    ],
)
def test_malformed_mapfiles_are_rejected(text):
    with pytest.raises(MapfileError):
        Mapfile.parse(text)
