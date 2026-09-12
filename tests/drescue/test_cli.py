import json

import pytest

from drescue.cli import (
    EXIT_INCOMPLETE,
    EXIT_OK,
    EXIT_USAGE,
    main,
    parse_domain,
    parse_size,
)

from . import samples

MiB = 1024 * 1024
LINUX_GUID = "0fc63daf-8483-4772-8e79-3d69d8477de4"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("512", 512), ("0x200", 512), ("4KiB", 4096), ("4kB", 4000), ("4k", 4000),
        ("1Mi", 1024 * 1024), ("2MB", 2_000_000), ("1G", 1_000_000_000),
        ("8s", 4096), ("1_000", 1000), ("1.5KiB", 1536),
    ],
)
def test_parse_size(text, expected):
    assert parse_size(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "4ZB", "-"])
def test_parse_size_rejects_nonsense(text):
    with pytest.raises(Exception):
        parse_size(text)


def test_parse_domain_accepts_both_forms():
    assert parse_domain("1MiB:2MiB") == (MiB, 2 * MiB)
    assert parse_domain("1MiB-3MiB") == (MiB, 2 * MiB)
    assert parse_domain("0x200:0x200") == (512, 512)
    with pytest.raises(Exception):
        parse_domain("5MiB-1MiB")
    with pytest.raises(Exception):
        parse_domain("nonsense")


@pytest.fixture
def disk(tmp_path):
    ext4_like = samples.fat32_boot_sector(label="PAYLOAD")
    return samples.make_gpt_image(
        str(tmp_path / "disk.img"),
        [(LINUX_GUID, "data", 1 * MiB, 8 * MiB, ext4_like)],
        32 * MiB,
    )


def test_rescue_status_and_verify_round_trip(disk, tmp_path, capsys):
    image, mapfile = str(tmp_path / "out.img"), str(tmp_path / "out.map")
    assert main(["rescue", disk, image, mapfile, "-q"]) == EXIT_OK
    assert open(image, "rb").read() == open(disk, "rb").read()

    assert main(["status", mapfile, "--json"]) == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert report["complete"] is True
    assert report["bytes"]["+"] == 32 * MiB

    assert main(["verify", disk, image, mapfile, "--json"]) == EXIT_OK
    verify = json.loads(capsys.readouterr().out)
    assert verify["match"] is True
    assert verify["mismatched"] == 0
    assert verify["sha256_source"] == verify["sha256_image"]


def test_verify_detects_a_corrupted_image(disk, tmp_path, capsys):
    image, mapfile = str(tmp_path / "out.img"), str(tmp_path / "out.map")
    main(["rescue", disk, image, mapfile, "-q"])
    with open(image, "r+b") as fh:
        fh.seek(4 * MiB)
        fh.write(b"\xde\xad\xbe\xef")
    assert main(["verify", disk, image, mapfile, "--json"]) == EXIT_INCOMPLETE
    report = json.loads(capsys.readouterr().out)
    assert report["match"] is False
    assert report["mismatched_ranges"]


def test_rescue_json_report(disk, tmp_path, capsys):
    out = main(["rescue", disk, str(tmp_path / "o.img"), str(tmp_path / "o.map"),
                "-q", "--json"])
    assert out == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert report["complete"] is True
    assert report["rescued"] == 32 * MiB
    assert report["bad_ranges"] == []


def test_rescue_domain_limits_the_copy(disk, tmp_path, capsys):
    main(["rescue", disk, str(tmp_path / "o.img"), str(tmp_path / "o.map"),
          "-q", "--json", "--domain", "1MiB:1MiB"])
    report = json.loads(capsys.readouterr().out)
    assert report["rescued"] == MiB
    assert report["complete"] is True  # complete *within the domain*


def test_rescue_domain_partition(disk, tmp_path, capsys):
    main(["rescue", disk, str(tmp_path / "o.img"), str(tmp_path / "o.map"),
          "-q", "--json", "--domain-partition", "1"])
    report = json.loads(capsys.readouterr().out)
    assert report["rescued"] == 8 * MiB


def test_rescue_refuses_an_unknown_partition(disk, tmp_path, capsys):
    assert main(["rescue", disk, str(tmp_path / "o.img"), "-q",
                 "--domain-partition", "9"]) == EXIT_USAGE
    assert "partition 9 not found" in capsys.readouterr().err


def test_rescue_refuses_to_copy_onto_itself(disk, capsys):
    assert main(["rescue", disk, disk]) == EXIT_USAGE
    assert "same object" in capsys.readouterr().err


def test_rescue_resumes_from_an_existing_mapfile(disk, tmp_path, capsys):
    image, mapfile = str(tmp_path / "o.img"), str(tmp_path / "o.map")
    main(["rescue", disk, image, mapfile, "-q"])
    main(["rescue", disk, image, mapfile, "-q", "--json"])
    report = json.loads(capsys.readouterr().out)
    assert report["complete"] is True


def test_scan_reports_partitions_and_filesystems(disk, capsys):
    assert main(["scan", disk, "--json"]) == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert report["scheme"] == "gpt"
    assert len(report["partitions"]) == 1
    part = report["partitions"][0]
    assert part["start"] == MiB and part["name"] == "data"
    assert part["filesystem"]["kind"] == "FAT32"
    assert part["filesystem"]["label"] == "PAYLOAD"


def test_scan_human_output_mentions_the_scheme(disk, capsys):
    assert main(["scan", disk]) == EXIT_OK
    out = capsys.readouterr().out
    assert "scheme:      gpt" in out
    assert "FAT32" in out


def test_carve_end_to_end_with_a_mapfile(tmp_path, capsys):
    from drescue.extents import BAD, FINISHED, ExtentMap
    from drescue.mapfile import Mapfile

    payload = samples.png()
    image = tmp_path / "img.bin"
    blob = bytearray(b"\0" * 8192)
    blob[512 : 512 + len(payload)] = payload
    blob[4096 : 4096 + len(payload)] = payload
    image.write_bytes(bytes(blob))

    emap = ExtentMap.covering(0, len(blob), FINISHED)
    emap.set_status(4096, 512, BAD)
    mapfile = tmp_path / "m.map"
    Mapfile(extents=emap, current_status="+").save(mapfile)

    assert main(["carve", str(image), "-o", str(tmp_path / "out"),
                 "-m", str(mapfile), "--json"]) == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert report["count"] == 2
    assert report["suspect"] == 1
    good = [f for f in report["files"] if not f["suspect"]][0]
    assert open(good["path"], "rb").read() == payload


def test_carve_dry_run_reports_without_writing(tmp_path, capsys):
    image = tmp_path / "img.bin"
    blob = bytearray(b"\0" * 4096)
    blob[0 : len(samples.png())] = samples.png()
    image.write_bytes(bytes(blob))
    assert main(["carve", str(image), "--json"]) == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert report["count"] == 1
    assert report["files"][0]["path"] == ""


def test_missing_file_is_a_clean_error(tmp_path, capsys):
    assert main(["scan", str(tmp_path / "nope.img")]) == EXIT_USAGE
    assert "drescue:" in capsys.readouterr().err


def test_unreadable_mapfile_is_a_clean_error(tmp_path, capsys):
    bad = tmp_path / "bad.map"
    bad.write_text("this is not a mapfile\n")
    assert main(["status", str(bad)]) == EXIT_USAGE
    assert "drescue:" in capsys.readouterr().err


def test_deep_scan_finds_a_volume_with_no_table_entry(tmp_path, capsys):
    """A disk whose partition table is gone still yields its volumes."""
    image = tmp_path / "wiped.img"
    with open(image, "wb") as fh:
        fh.truncate(16 * MiB)
        fh.seek(4 * MiB)
        fh.write(samples.fat32_boot_sector(label="ORPHAN"))
    assert main(["scan", str(image), "--deep", "--json"]) == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert report["scheme"] == "none"
    assert [f["label"] for f in report["lost_filesystems"]] == ["ORPHAN"]
    assert report["lost_filesystems"][0]["offset"] == 4 * MiB


def test_deep_scan_on_a_bare_volume_reports_it_once(tmp_path, capsys):
    image = tmp_path / "bare.img"
    with open(image, "wb") as fh:
        fh.truncate(8 * MiB)
        fh.seek(0)
        fh.write(samples.fat32_boot_sector(label="WHOLE"))
        fh.seek(4 * MiB)
        fh.write(samples.ntfs_boot_sector())
    assert main(["scan", str(image), "--deep", "--json"]) == EXIT_OK
    report = json.loads(capsys.readouterr().out)
    assert report["filesystem"]["label"] == "WHOLE"
    assert [f["kind"] for f in report["lost_filesystems"]] == ["NTFS"]
