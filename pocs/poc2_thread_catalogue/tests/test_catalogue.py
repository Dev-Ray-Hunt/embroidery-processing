"""POC 2 catalogue verification.

Source-parser tests run against the PDFs/palettes in data/madeira_sources/
(gitignored; re-fetch script in data/README.md) and skip cleanly when absent.
Pure color-math tests always run.
"""

from __future__ import annotations

import collections
import warnings

import pytest

warnings.filterwarnings("ignore", message=".*(SciPy|Matplotlib).*")

from pocs.poc2_thread_catalogue.src import catalogue, sources  # noqa: E402

SOURCES_PRESENT = (sources.SOURCES_DIR / "inkstitch_madeira_rayon.gpl").exists() and (
    sources.SOURCES_DIR / "madeira_official_colour_cards.pdf"
).exists()

needs_sources = pytest.mark.skipif(
    not SOURCES_PRESENT, reason="madeira source files not present (gitignored data/)"
)


# --------------------------- color math (always run) -------------------------


def test_lab_conversion_anchors():
    """Known sRGB->Lab D65 anchor values (CIE 2-degree observer)."""
    white = catalogue.rgb_to_lab((255, 255, 255))
    assert white[0] == pytest.approx(100.0, abs=0.1)
    assert abs(white[1]) < 0.5 and abs(white[2]) < 0.5
    black = catalogue.rgb_to_lab((0, 0, 0))
    assert black[0] == pytest.approx(0.0, abs=0.1)
    red = catalogue.rgb_to_lab((255, 0, 0))
    assert red[0] == pytest.approx(53.2, abs=1.0)
    assert red[1] == pytest.approx(80.1, abs=1.5)
    assert red[2] == pytest.approx(67.2, abs=1.5)


def test_lab_round_trip_stability():
    """rgb -> lab -> rgb must come back within 1/255 per channel."""
    import colour
    import numpy as np

    for rgb in [(0, 0, 0), (255, 255, 255), (182, 15, 47), (45, 42, 45), (235, 234, 255)]:
        lab = catalogue.rgb_to_lab(rgb)
        back = colour.XYZ_to_sRGB(colour.Lab_to_XYZ(np.array(lab)))
        back255 = tuple(round(float(v) * 255) for v in back)
        assert all(abs(a - b) <= 1 for a, b in zip(rgb, back255, strict=True)), (
            f"{rgb} -> {lab} -> {back255}"
        )


def test_color_family_anchors():
    cases = [
        ((40, 41, 42), "black"),
        ((227, 229, 251), "white"),  # Super White: faint blue cast
        ((128, 128, 128), "neutral"),
        ((182, 15, 47), "red"),
        ((243, 82, 34), "orange"),
        ((255, 199, 44), "yellow"),
        ((0, 121, 52), "green"),
        ((27, 63, 148), "blue"),
        ((93, 35, 139), "purple"),
        ((246, 141, 169), "pink"),
        ((94, 73, 52), "brown"),
    ]
    for rgb, expected in cases:
        lab = catalogue.rgb_to_lab(rgb)
        assert catalogue.color_family(rgb, lab) == expected, f"{rgb} -> expected {expected}"


# --------------------------- sources & build (need data) ---------------------


@needs_sources
def test_source_parsers_meet_floors():
    floors = {
        "official_classic": 180,
        "official_polyneon": 380,
        "ciainc_polyneon": 320,
        "ezstitch_polyneon": 300,
        "inkstitch_rayon": 320,
        "inkstitch_polyneon": 320,
    }
    for name, fn in sources.ALL_PARSERS.items():
        entries = fn()
        assert len(entries) >= floors[name], f"{name}: {len(entries)} < floor {floors[name]}"
        for e in entries:
            assert e["catalog"].isdigit() and len(e["catalog"]) == 4
            assert all(0 <= c <= 255 for c in e["rgb"])


@needs_sources
def test_official_names_cover_both_lines():
    names = sources.parse_official_names()
    assert len(names[sources.LINE_CLASSIC]) >= 350
    assert len(names[sources.LINE_POLYNEON]) >= 380
    # Classic codes are 1000-1499 — the membership fact the merge relies on.
    assert all(1000 <= int(c) <= 1499 for c in names[sources.LINE_CLASSIC])


@pytest.fixture(scope="module")
def built():
    if not SOURCES_PRESENT:
        pytest.skip("madeira source files not present")
    return catalogue.build()


@needs_sources
def test_catalogue_meets_poc_pass_criteria(built):
    """POC 2 pass/fail: >= 200 threads, both lines covered."""
    assert built["stats"]["total"] >= 200
    per_line = built["stats"]["per_line"]
    assert per_line.get(sources.LINE_CLASSIC, 0) >= 100
    assert per_line.get(sources.LINE_POLYNEON, 0) >= 100


@needs_sources
def test_catalogue_integrity(built):
    threads = built["threads"]
    # No duplicate (line, catalog) pairs.
    keys = [(t["line"], t["catalog_number"]) for t in threads]
    dupes = [k for k, n in collections.Counter(keys).items() if n > 1]
    assert not dupes, f"duplicate entries: {dupes[:5]}"
    for t in threads:
        assert all(0 <= c <= 255 for c in t["rgb"])
        assert t["hex"] == "#{:02x}{:02x}{:02x}".format(*t["rgb"])
        assert 0 <= t["lab"][0] <= 100
        assert t["color_family"] in {
            "white",
            "yellow",
            "orange",
            "red",
            "pink",
            "purple",
            "blue",
            "green",
            "brown",
            "neutral",
            "black",
        }
        assert t["rgb_source"] in t["source_rgb"]
        assert list(t["source_rgb"][t["rgb_source"]]) == list(t["rgb"])
        assert t["fiber"] == ("Rayon" if t["line"] == sources.LINE_CLASSIC else "Polyester")


@needs_sources
def test_official_sources_win_when_present(built):
    """Reconciliation rule: official swatch colors beat third-party values."""
    for t in built["threads"]:
        official = [s for s in t["source_rgb"] if s.startswith("official_")]
        if official:
            assert t["rgb_source"] in official, (
                f"{t['catalog_number']}: {t['rgb_source']} won over official source"
            )


@needs_sources
def test_known_anchor_threads(built):
    """Famous catalog numbers must land near their known colors."""
    lookup = {(t["line"], t["catalog_number"]): t for t in built["threads"]}

    def assert_close(line, code, target_rgb, tol=60):
        t = lookup[(line, code)]
        d = sum((a - b) ** 2 for a, b in zip(t["rgb"], target_rgb, strict=True)) ** 0.5
        assert d <= tol, f"{line} {code} = {t['rgb']}, expected near {target_rgb}"

    assert_close(sources.LINE_CLASSIC, "1000", (40, 40, 42))  # Black
    assert_close(sources.LINE_CLASSIC, "1001", (235, 235, 245))  # Super White
    assert_close(sources.LINE_POLYNEON, "1800", (45, 42, 45))  # Emerald Black
    assert_close(sources.LINE_POLYNEON, "1801", (240, 240, 250))  # Super White
    assert_close(sources.LINE_POLYNEON, "1678", (243, 82, 34))  # Pumpkin


@needs_sources
def test_conflict_rate_is_bounded(built):
    """Sources disagreeing wildly on >15% of entries would mean the
    extraction itself is broken, not the sources."""
    assert built["stats"]["conflicts"] / built["stats"]["total"] < 0.15
