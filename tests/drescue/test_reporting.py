import io

from drescue.extents import BAD, FINISHED, NON_TRIED, ExtentMap
from drescue.reporting import (
    StatusPrinter,
    human_bytes,
    human_rate,
    human_time,
    map_legend,
    render_map,
    summary_lines,
)
from drescue.rescue import Stats


def test_human_bytes_uses_si_units():
    assert human_bytes(0) == "0 B"
    assert human_bytes(999) == "999 B"
    assert human_bytes(1000) == "1.0 kB"
    assert human_bytes(1_500_000) == "1.5 MB"
    assert human_rate(2_000_000) == "2.0 MB/s"


def test_human_time():
    assert human_time(5) == "5s"
    assert human_time(65) == "1m 5s"
    assert human_time(3725) == "1h 2m 5s"
    assert human_time(-1) == "0s"


def test_render_map_shows_one_glyph_per_cell():
    m = ExtentMap.covering(0, 1000, FINISHED)
    assert render_map(m, 10) == "#" * 10
    assert render_map(m, 0) == ""
    assert render_map(ExtentMap(), 10) == ""


def test_render_map_never_hides_a_bad_sector_in_a_good_cell():
    m = ExtentMap.covering(0, 1_000_000, FINISHED)
    m.set_status(500_000, 512, BAD)
    rendered = render_map(m, 10)
    assert rendered.count("X") == 1
    assert rendered == "#####X####"


def test_render_map_severity_order():
    m = ExtentMap.covering(0, 100, FINISHED)
    m.set_status(0, 10, NON_TRIED)
    assert render_map(m, 1) == "."  # non-tried outranks finished
    m.set_status(0, 10, BAD)
    assert render_map(m, 1) == "X"  # bad outranks everything


def test_summary_lines_cover_every_status():
    m = ExtentMap.covering(0, 1000)
    lines = summary_lines(m)
    assert len(lines) == 6
    assert "non-tried" in lines[0] and "100.00%" in lines[0]
    assert "total" in lines[-1]


def test_legend_lists_the_glyphs():
    legend = map_legend()
    for glyph in "#.*/X":
        assert glyph in legend


def test_status_printer_writes_a_single_line_when_not_a_tty():
    stream = io.StringIO()
    printer = StatusPrinter(stream, size=1000)
    printer.update(Stats(rescued=500, current_rate=1000.0), ExtentMap.covering(0, 1000))
    out = stream.getvalue()
    assert out.count("\n") == 1
    assert "rescued" in out


def test_status_printer_redraws_in_place_on_a_tty():
    class Tty(io.StringIO):
        def isatty(self):
            return True

    stream = Tty()
    printer = StatusPrinter(stream, size=1000, show_map=False)
    stats = Stats(rescued=500)
    printer.update(stats, ExtentMap.covering(0, 1000))
    first = stream.getvalue()
    printer.update(stats, ExtentMap.covering(0, 1000))
    assert "\033[" in stream.getvalue()[len(first):]  # cursor moved back up
    printer.finish()
