import random

import pytest

from drescue.extents import BAD, FINISHED, NON_TRIED, ExtentMap
from drescue.mapfile import Mapfile
from drescue.rescue import RescueConfig, Rescuer

from .fakes import FaultyReader, MemoryWriter

SECTOR = 512
SIZE = 256 * 1024  # 512 sectors


@pytest.fixture
def payload():
    rng = random.Random(20240912)
    return bytes(rng.getrandbits(8) for _ in range(SIZE))


def run(reader, *, config=None, mapfile=None, writer=None):
    writer = writer if writer is not None else MemoryWriter(reader.size)
    mapfile = mapfile or Mapfile(extents=ExtentMap.covering(0, reader.size))
    cfg = config or RescueConfig(sector_size=SECTOR)
    rescuer = Rescuer(reader, writer, mapfile, cfg)
    stats = rescuer.run()
    return stats, mapfile.extents, writer


def assert_image_matches(writer, payload, bad_sectors):
    """Every good sector is byte-exact; no bad sector was invented."""
    for sector in range(len(payload) // SECTOR):
        lo, hi = sector * SECTOR, (sector + 1) * SECTOR
        if sector in bad_sectors:
            assert not any(writer.written[lo:hi]), f"sector {sector} should be untouched"
        else:
            assert all(writer.written[lo:hi]), f"sector {sector} missing"
            assert writer.data[lo:hi] == payload[lo:hi], f"sector {sector} corrupted"


def test_clean_device_is_copied_completely(payload):
    reader = FaultyReader(payload, sector_size=SECTOR)
    stats, emap, writer = run(reader)
    assert emap.is_done()
    assert stats.rescued == SIZE
    assert stats.errors == 0
    assert bytes(writer.data) == payload


def test_bad_sectors_are_isolated_to_the_sector(payload):
    bad = {100, 101, 102, 300, 400, 401}
    reader = FaultyReader(payload, bad, SECTOR)
    stats, emap, writer = run(reader)
    assert stats.bad == len(bad) * SECTOR
    assert stats.rescued == SIZE - len(bad) * SECTOR
    assert_image_matches(writer, payload, bad)
    assert sorted(emap.ranges(BAD)) == [(51200, 1536), (153600, 512), (204800, 1024)]


def test_a_bad_sector_does_not_cost_a_whole_cluster(payload):
    """The point of trim+scrape: one bad sector must not lose its 127 neighbours."""
    reader = FaultyReader(payload, {200}, SECTOR)
    _, emap, _ = run(reader)
    assert emap.bytes_with(BAD) == SECTOR


def test_copy_phase_skips_ahead_instead_of_grinding(payload):
    """A large damaged region must not be read sector by sector during copy."""
    bad = set(range(100, 300))  # 100 KiB of contiguous damage
    reader = FaultyReader(payload, bad, SECTOR)
    cfg = RescueConfig(sector_size=SECTOR, trim=False, scrape=False, retries=0)
    run(reader, config=cfg)
    # 200 unreadable sectors, but copy gives up on them in a handful of reads.
    assert reader.error_reads < 10
    assert len(reader.reads) < 20


def test_trim_and_scrape_reclaim_the_sectors_around_the_damage(payload):
    """Copy loses whole clusters on purpose; trim and scrape win them back."""
    bad = set(range(100, 300))
    coarse = FaultyReader(payload, bad, SECTOR)
    run(coarse, config=RescueConfig(sector_size=SECTOR, trim=False, scrape=False,
                                    retries=0))

    reader = FaultyReader(payload, bad, SECTOR)
    _, emap, writer = run(reader)  # full copy -> trim -> scrape -> retry
    assert emap.bytes_with(BAD) == len(bad) * SECTOR
    assert_image_matches(writer, payload, bad)


def test_retry_pass_recovers_intermittent_sectors(payload):
    """Sectors that fail twice then succeed are exactly what retries are for."""
    reader = FaultyReader(payload, sector_size=SECTOR, transient={250: 2, 251: 2})
    _, emap, writer = run(reader, config=RescueConfig(sector_size=SECTOR, retries=3))
    assert emap.is_done()
    assert bytes(writer.data) == payload
    assert reader.dropped_cache > 0  # retries bypassed the cache


def test_retries_disabled_leaves_flaky_sectors_bad(payload):
    reader = FaultyReader(payload, sector_size=SECTOR, transient={250: 5})
    _, emap, _ = run(reader, config=RescueConfig(sector_size=SECTOR, retries=0))
    assert emap.bytes_with(BAD) == SECTOR


def test_reverse_direction_produces_the_same_image(payload):
    bad = {10, 11, 500}
    forward = run(FaultyReader(payload, bad, SECTOR))
    backward = run(FaultyReader(payload, bad, SECTOR),
                   config=RescueConfig(sector_size=SECTOR, reverse=True))
    assert bytes(forward[2].data) == bytes(backward[2].data)
    assert forward[1].totals() == backward[1].totals()


def test_domain_limits_all_work_to_the_given_range(payload):
    reader = FaultyReader(payload, sector_size=SECTOR)
    cfg = RescueConfig(sector_size=SECTOR, domain=[(64 * 1024, 32 * 1024)])
    stats, emap, writer = run(reader, config=cfg)
    assert stats.rescued == 32 * 1024
    assert emap.is_done(cfg.domain)
    assert not emap.is_done()
    assert all(pos >= 64 * 1024 and pos < 96 * 1024 for pos, _ in reader.reads)


def test_interrupting_saves_progress_and_resuming_finishes_the_job(payload, tmp_path):
    path = tmp_path / "d.map"
    reader = FaultyReader(payload, sector_size=SECTOR)
    mapfile = Mapfile(extents=ExtentMap.covering(0, SIZE))
    writer = MemoryWriter(SIZE)

    budget = {"n": 6}  # stop after a handful of 4 KiB reads

    def stop():
        budget["n"] -= 1
        return budget["n"] <= 0

    small = RescueConfig(sector_size=SECTOR, cluster_size=8)
    first = Rescuer(reader, writer, mapfile, small,
                    mapfile_path=str(path), should_stop=stop)
    first.run()
    partial = Mapfile.load(path)
    assert 0 < partial.extents.bytes_with(FINISHED) < SIZE

    second = Rescuer(FaultyReader(payload, sector_size=SECTOR), writer, partial,
                     small, mapfile_path=str(path))
    second.run()
    assert partial.extents.is_done()
    assert bytes(writer.data) == payload


def test_resuming_does_not_re_read_finished_areas(payload):
    reader = FaultyReader(payload, sector_size=SECTOR)
    emap = ExtentMap.covering(0, SIZE)
    emap.set_status(0, SIZE - 4096, FINISHED)
    run(reader, mapfile=Mapfile(extents=emap))
    assert all(pos >= SIZE - 4096 for pos, _ in reader.reads)


def test_max_errors_aborts_early(payload):
    reader = FaultyReader(payload, set(range(0, 512, 4)), SECTOR)
    cfg = RescueConfig(sector_size=SECTOR, max_errors=3)
    stats, emap, _ = run(reader, config=cfg)
    assert stats.errors == 3
    assert not emap.is_done()


def test_fill_bad_marks_unreadable_areas_in_the_image(payload):
    reader = FaultyReader(payload, {7}, SECTOR)
    cfg = RescueConfig(sector_size=SECTOR, fill_bad=0xAA, retries=0)
    _, _, writer = run(reader, config=cfg)
    assert writer.data[7 * SECTOR : 8 * SECTOR] == bytearray([0xAA]) * SECTOR


def test_mapfile_status_ends_as_finished_when_complete(payload, tmp_path):
    path = tmp_path / "x.map"
    mf = Mapfile(extents=ExtentMap.covering(0, SIZE))
    Rescuer(FaultyReader(payload, sector_size=SECTOR), MemoryWriter(SIZE), mf,
            RescueConfig(sector_size=SECTOR), mapfile_path=str(path)).run()
    assert Mapfile.load(path).current_status == "+"


def test_rate_limit_slows_the_run_down(payload):
    reader = FaultyReader(payload[: 64 * 1024], sector_size=SECTOR)
    cfg = RescueConfig(sector_size=SECTOR, rate_limit=256 * 1024, cluster_size=8)
    stats, emap, _ = run(reader, config=cfg)
    assert emap.is_done()
    assert stats.run_time > 0.05


def test_reading_without_a_writer_is_a_pure_survey(payload):
    reader = FaultyReader(payload, {3}, SECTOR)
    mf = Mapfile(extents=ExtentMap.covering(0, SIZE))
    stats = Rescuer(reader, None, mf, RescueConfig(sector_size=SECTOR)).run()
    assert stats.bad == SECTOR
    assert mf.extents.bytes_with(FINISHED) == SIZE - SECTOR


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        RescueConfig(sector_size=500)
    with pytest.raises(ValueError):
        RescueConfig(cluster_size=0)
