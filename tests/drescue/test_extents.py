import pytest

from drescue.extents import (
    BAD,
    FINISHED,
    NON_TRIED,
    NON_TRIMMED,
    Extent,
    ExtentMap,
    align_down,
    align_up,
    clip,
)


def statuses(m):
    return [(e.pos, e.size, e.status) for e in m]


def test_covering_is_single_extent():
    m = ExtentMap.covering(0, 1000)
    assert statuses(m) == [(0, 1000, NON_TRIED)]
    assert m.size == 1000 and m.start == 0 and m.end == 1000


def test_set_status_splits_and_keeps_contiguity():
    m = ExtentMap.covering(0, 1000)
    m.set_status(400, 100, BAD)
    assert statuses(m) == [(0, 400, NON_TRIED), (400, 100, BAD), (500, 500, NON_TRIED)]
    assert sum(e.size for e in m) == 1000


def test_adjacent_same_status_extents_merge():
    m = ExtentMap.covering(0, 1000)
    m.set_status(0, 500, FINISHED)
    m.set_status(500, 500, FINISHED)
    assert statuses(m) == [(0, 1000, FINISHED)]


def test_overwriting_a_span_replaces_everything_under_it():
    m = ExtentMap.covering(0, 1000)
    for pos in range(0, 1000, 100):
        m.set_status(pos, 50, BAD)
    m.set_status(0, 1000, FINISHED)
    assert statuses(m) == [(0, 1000, FINISHED)]


def test_set_status_is_clipped_to_the_map():
    m = ExtentMap.covering(100, 100)
    m.set_status(0, 1000, BAD)
    assert statuses(m) == [(100, 100, BAD)]
    m.set_status(500, 10, FINISHED)  # entirely outside
    assert statuses(m) == [(100, 100, BAD)]


def test_totals_and_is_done():
    m = ExtentMap.covering(0, 1000)
    m.set_status(0, 900, FINISHED)
    assert m.totals()[FINISHED] == 900
    assert m.bytes_with(NON_TRIED) == 100
    assert not m.is_done()
    m.set_status(900, 100, FINISHED)
    assert m.is_done()


def test_domain_restricts_ranges_and_totals():
    m = ExtentMap.covering(0, 1000)
    m.set_status(0, 1000, BAD)
    assert list(m.ranges(BAD, domain=[(200, 100)])) == [(200, 100)]
    assert m.bytes_with(BAD, domain=[(200, 100)]) == 100
    assert m.is_done(domain=[(0, 0)])


def test_status_at():
    m = ExtentMap.covering(0, 1000)
    m.set_status(400, 100, NON_TRIMMED)
    assert m.status_at(0) == NON_TRIED
    assert m.status_at(450) == NON_TRIMMED
    assert m.status_at(999) == NON_TRIED


def test_fill_gaps_extends_a_partial_map():
    m = ExtentMap([Extent(0, 100, FINISHED)])
    m.fill_gaps(0, 1000)
    assert statuses(m) == [(0, 100, FINISHED), (100, 900, NON_TRIED)]


def test_clip_without_domain_drops_empty_ranges():
    assert list(clip([(0, 10), (10, 0)], None)) == [(0, 10)]


def test_non_contiguous_map_is_rejected():
    with pytest.raises(ValueError):
        ExtentMap([Extent(0, 10, FINISHED), Extent(20, 10, FINISHED)])


def test_alignment_helpers():
    assert align_down(1000, 512) == 512
    assert align_up(1000, 512) == 1024
    assert align_up(1024, 512) == 1024
