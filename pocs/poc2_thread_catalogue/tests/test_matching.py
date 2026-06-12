"""Tests for the color matching engine (POC 2 Step 2).

Structure
---------
* pure_math — CIEDE2000 against Sharma et al. 2005 reference pairs;
              CIE76 against hand-computed values.  No data files needed.
* unit (fixture catalogue) — ranking sanity, hex parsing, match_palette
  properties.  Uses an inline 10-thread catalogue so these run without the
  gitignored outputs/poc2/madeira_catalogue.json.
* integration — spot-checks against the full built catalogue; skipped if the
  file is absent.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
import pytest

warnings.filterwarnings("ignore", message=".*(SciPy|Matplotlib).*")

from pocs.poc2_thread_catalogue.src.matching import (  # noqa: E402
    _rgb_to_lab,
    find_closest_threads,
    match_palette,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

CATALOGUE_PATH = (
    __import__("pathlib").Path(__file__).resolve().parents[3]
    / "outputs"
    / "poc2"
    / "madeira_catalogue.json"
)

catalogue_present = pytest.mark.skipif(
    not CATALOGUE_PATH.exists(),
    reason="madeira_catalogue.json not present (run catalogue builder first)",
)


def _thread(catalog: str, name: str, rgb: tuple[int, int, int]) -> dict:
    """Build a minimal fixture thread dict with auto-computed Lab."""
    lab = _rgb_to_lab(rgb)
    return {
        "catalog_number": catalog,
        "color_name": name,
        "brand": "Madeira Classic Rayon 40",
        "line": "Classic Rayon 40",
        "rgb": list(rgb),
        "hex": "#{:02x}{:02x}{:02x}".format(*rgb),
        "lab": [round(float(v), 4) for v in lab],
        "color_family": "black" if lab[0] < 25 else "white" if lab[0] > 85 else "neutral",
        "weight": "40",
        "fiber": "Rayon",
    }


# 10-thread inline fixture catalogue covering light, dark, and saturated colors
FIXTURE_CATALOGUE = [
    _thread("1000", "Black", (40, 40, 40)),
    _thread("1001", "Super White", (235, 235, 235)),
    _thread("1100", "Christmas Red", (182, 15, 47)),
    _thread("1101", "Royal Blue", (27, 63, 148)),
    _thread("1102", "Forest Green", (0, 121, 52)),
    _thread("1103", "Sunflower", (255, 199, 44)),
    _thread("1104", "Pumpkin", (243, 82, 34)),
    _thread("1105", "Purple", (93, 35, 139)),
    _thread("1106", "Dark Grey", (80, 80, 80)),
    _thread("1107", "Light Blue", (100, 149, 237)),
]


# ---------------------------------------------------------------------------
# Pure math: CIEDE2000 against Sharma, Wu & Dalal 2005 (Table 1)
# Tolerance 0.05 per the published acceptance criterion.
# ---------------------------------------------------------------------------

# 8 representative pairs from the standard 34-pair test set
# Format: (Lab1, Lab2, expected_ΔE2000)
SHARMA_PAIRS = [
    # Near-blue — tests chroma and hue weighting
    ([50.0000, 2.6772, -79.7751], [50.0000, 0.0000, -82.7485], 2.0425),
    ([50.0000, 3.1571, -77.2803], [50.0000, 0.0000, -82.7485], 2.8615),
    # Near-neutral gray — tests basic computation
    ([50.0000, 0.0000, 0.0000], [50.0000, -1.0000, 2.0000], 2.3669),
    # Near-neutral with tricky hue angle
    ([50.0000, 2.4900, -0.0010], [50.0000, -2.4900, 0.0009], 7.1792),
    # Saturated yellowish-green
    ([60.2574, -34.0099, 36.2677], [60.4626, -34.1751, 39.4387], 1.2644),
    # Blue-purple
    ([22.7233, 20.0904, -46.6940], [23.0331, 14.9730, -42.5619], 2.0373),
    # Near-white
    ([90.9257, -0.5406, -0.9208], [88.6381, -0.8985, -0.7239], 1.5381),
    # Near-black, small distance
    ([2.0776, 0.0795, -1.1350], [0.9033, -0.0636, -0.5514], 0.9082),
]


@pytest.mark.parametrize("lab1,lab2,expected", SHARMA_PAIRS)
def test_ciede2000_sharma_reference(lab1, lab2, expected):
    """CIEDE2000 must match the Sharma 2005 published reference values."""
    import colour

    got = float(colour.difference.delta_E_CIE2000(np.array(lab1), np.array(lab2)))
    assert abs(got - expected) < 0.05, (
        f"CIEDE2000({lab1}, {lab2}) = {got:.4f}, expected {expected:.4f} (tol 0.05)"
    )


# ---------------------------------------------------------------------------
# Pure math: CIE76 against hand-computed values
# ΔE76 = sqrt(ΔL² + Δa² + Δb²)
# ---------------------------------------------------------------------------

CIE76_CASES = [
    # Axis-aligned differences — trivially verifiable
    ([50.0, 0.0, 0.0], [55.0, 0.0, 0.0], 5.0),
    ([50.0, 0.0, 0.0], [50.0, 3.0, 4.0], 5.0),
    # Pure lightness range
    ([0.0, 0.0, 0.0], [100.0, 0.0, 0.0], 100.0),
    # Diagonal 3-D
    ([20.0, 10.0, 5.0], [25.0, 15.0, 5.0], math.sqrt(25 + 25)),
    # Identical — zero distance
    ([60.0, -20.0, 30.0], [60.0, -20.0, 30.0], 0.0),
]


@pytest.mark.parametrize("lab1,lab2,expected", CIE76_CASES)
def test_cie76_hand_computed(lab1, lab2, expected):
    """CIE76 (Euclidean in Lab) must match hand-computed Euclidean distance."""
    got = float(np.linalg.norm(np.array(lab1) - np.array(lab2)))
    assert abs(got - expected) < 1e-6, f"CIE76({lab1}, {lab2}) = {got}, expected {expected}"


# ---------------------------------------------------------------------------
# Unit tests using FIXTURE_CATALOGUE (no data files required)
# ---------------------------------------------------------------------------


class TestFindClosestThreads:
    def test_exact_match_returns_delta_e_zero_ciede2000(self):
        """A color exactly present in the catalogue must be ranked first with ΔE ≈ 0.

        The fixture stores Lab rounded to 4 decimal places; the query recomputes
        Lab at full float64 precision, so the residual is O(1e-5) — not zero,
        but well below any perceptible threshold (JND ≈ 1.0).
        """
        rgb = (40, 40, 40)  # "Black"
        results = find_closest_threads(
            rgb, top_n=1, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
        )
        assert len(results) == 1
        cat_num, _name, de, _rgb = results[0]
        assert cat_num == "1000", f"Expected Black (1000), got {cat_num}"
        assert de < 1e-3, f"Exact match should have ΔE ≈ 0, got {de}"

    def test_exact_match_returns_delta_e_zero_all_algorithms(self):
        """Exact match -> ΔE ≈ 0 for all four algorithms."""
        rgb = (182, 15, 47)  # "Christmas Red"
        for algo in ("ciede2000", "cie76", "rgb", "cmc"):
            results = find_closest_threads(
                rgb, top_n=1, algorithm=algo, catalogue=FIXTURE_CATALOGUE
            )
            _cat, _name, de, _rgb = results[0]
            assert de < 1e-3, f"Exact match delta-E should be ≈ 0 for {algo}, got {de}"

    def test_results_sorted_ascending(self):
        """Results must be ordered by delta-E, smallest first."""
        results = find_closest_threads(
            (128, 128, 128), top_n=5, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
        )
        assert len(results) == 5
        des = [r[2] for r in results]
        assert des == sorted(des), f"Results not sorted: {des}"

    def test_top_n_respected(self):
        for n in (1, 3, 5, 10):
            results = find_closest_threads(
                (100, 100, 100), top_n=n, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
            )
            assert len(results) == min(n, len(FIXTURE_CATALOGUE))

    def test_near_black_returns_black_family(self):
        """Very dark input should rank the black thread first."""
        results = find_closest_threads(
            (5, 5, 5), top_n=3, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
        )
        top_cat = results[0][0]
        # Both Black (1000) and Dark Grey (1106) are dark; black should win
        assert top_cat in ("1000", "1106"), f"Expected a dark thread at top-1, got {top_cat}"
        # delta-E should be small (< 10 for near-black vs black)
        assert results[0][2] < 15.0

    def test_near_white_returns_white_thread(self):
        """Near-white input should return Super White as top match."""
        results = find_closest_threads(
            (240, 240, 240), top_n=1, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
        )
        assert results[0][0] == "1001", f"Expected Super White (1001), got {results[0][0]}"

    def test_hex_string_accepted(self):
        """Hex strings like '#b60f2f' must produce the same result as the RGB tuple."""
        rgb_result = find_closest_threads(
            (182, 15, 47), top_n=3, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
        )
        hex_result = find_closest_threads(
            "#b60f2f", top_n=3, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
        )
        assert [r[0] for r in rgb_result] == [r[0] for r in hex_result]
        for r, h in zip(rgb_result, hex_result, strict=True):
            assert abs(r[2] - h[2]) < 1e-6

    def test_hex_without_hash_accepted(self):
        rgb_result = find_closest_threads(
            (40, 40, 40), top_n=1, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
        )
        hex_result = find_closest_threads(
            "282828", top_n=1, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
        )
        assert rgb_result[0][0] == hex_result[0][0]

    def test_all_four_algorithms_return_results(self):
        """All four algorithms must return results (no exceptions)."""
        for algo in ("ciede2000", "cie76", "rgb", "cmc"):
            results = find_closest_threads(
                (100, 150, 200), top_n=3, algorithm=algo, catalogue=FIXTURE_CATALOGUE
            )
            assert len(results) == 3, f"Algorithm {algo} returned wrong count"
            assert all(r[2] >= 0 for r in results), f"Algorithm {algo} returned negative delta-E"

    def test_result_tuple_structure(self):
        """Each result must be a 4-tuple: (catalog_str, name_or_None, float, rgb_tuple)."""
        results = find_closest_threads(
            (50, 100, 150), top_n=2, algorithm="ciede2000", catalogue=FIXTURE_CATALOGUE
        )
        for cat, name, de, rgb in results:
            assert isinstance(cat, str)
            assert name is None or isinstance(name, str)
            assert isinstance(de, float) and de >= 0
            assert len(rgb) == 3 and all(0 <= c <= 255 for c in rgb)

    def test_line_filter(self):
        """Line filter must restrict results to the specified thread line."""
        mixed_cat = FIXTURE_CATALOGUE[:5] + [
            {**FIXTURE_CATALOGUE[5], "catalog_number": "T999", "line": "Polyneon 40"}
        ]
        results = find_closest_threads(
            (100, 100, 100),
            top_n=10,
            algorithm="ciede2000",
            line="Classic Rayon 40",
            catalogue=mixed_cat,
        )
        lines = {r[0] for r in results}
        assert "T999" not in lines, "Line filter should exclude Polyneon threads"

    def test_algorithm_rankings_differ_on_saturated_color(self):
        """The four algorithms need not agree on rank order for a saturated color — just
        verify they all produce valid, sorted results."""
        for algo in ("ciede2000", "cie76", "rgb", "cmc"):
            results = find_closest_threads(
                (255, 0, 128),  # vivid pink not in fixture
                top_n=5,
                algorithm=algo,
                catalogue=FIXTURE_CATALOGUE,
            )
            des = [r[2] for r in results]
            assert des == sorted(des), f"{algo}: results not sorted"


# ---------------------------------------------------------------------------
# Unit tests: match_palette
# ---------------------------------------------------------------------------


class TestMatchPalette:
    def test_greedy_returns_one_result_per_input(self):
        colors = [(40, 40, 40), (182, 15, 47), (235, 235, 235)]
        result = match_palette(colors, strategy="greedy", catalogue=FIXTURE_CATALOGUE)
        assert len(result["assignments"]) == len(colors)
        assert result["strategy"] == "greedy"

    def test_greedy_hex_colors(self):
        colors = ["#282828", "#b60f2f", "#ebebeb"]
        result = match_palette(colors, strategy="greedy", catalogue=FIXTURE_CATALOGUE)
        assert len(result["assignments"]) == 3

    def test_greedy_worst_delta_e_is_max(self):
        colors = [(40, 40, 40), (0, 121, 52), (255, 199, 44)]
        result = match_palette(colors, strategy="greedy", catalogue=FIXTURE_CATALOGUE)
        de_values = [v[2] for v in result["assignments"].values()]
        assert abs(result["worst_delta_e"] - max(de_values)) < 1e-6

    def test_constrained_respects_thread_limit(self):
        """Constrained strategy must use no more than max_threads unique threads."""
        colors = [
            (40, 40, 40),
            (80, 80, 80),
            (120, 120, 120),
            (182, 15, 47),
            (27, 63, 148),
            (0, 121, 52),
        ]
        for limit in (1, 2, 3):
            result = match_palette(
                colors, strategy="constrained", max_threads=limit, catalogue=FIXTURE_CATALOGUE
            )
            used_cats = {v[0] for v in result["assignments"].values()}
            assert len(used_cats) <= limit, (
                f"max_threads={limit} but got {len(used_cats)} unique threads: {used_cats}"
            )

    def test_constrained_more_threads_never_worse(self):
        """Adding more threads can only reduce the worst-case delta-E (monotone property).

        The greedy k-center heuristic selects threads one at a time; each new
        thread can only improve best_so_far, so worst_delta_e(k) ≥ worst_delta_e(k+1).
        """
        # Use colors NOT in the fixture to get non-zero delta-E values
        colors = [(60, 80, 100), (200, 50, 50), (50, 200, 100), (100, 100, 200)]
        results_k1 = match_palette(
            colors, strategy="constrained", max_threads=1, catalogue=FIXTURE_CATALOGUE
        )
        results_k2 = match_palette(
            colors, strategy="constrained", max_threads=2, catalogue=FIXTURE_CATALOGUE
        )
        results_k4 = match_palette(
            colors, strategy="constrained", max_threads=4, catalogue=FIXTURE_CATALOGUE
        )
        assert results_k1["worst_delta_e"] >= results_k2["worst_delta_e"] - 1e-6, (
            "k=1 worst should be ≥ k=2 worst"
        )
        assert results_k2["worst_delta_e"] >= results_k4["worst_delta_e"] - 1e-6, (
            "k=2 worst should be ≥ k=4 worst"
        )

    def test_constrained_requires_max_threads(self):
        with pytest.raises(ValueError, match="max_threads"):
            match_palette([(40, 40, 40)], strategy="constrained", catalogue=FIXTURE_CATALOGUE)

    def test_cluster_merges_similar_colors(self):
        """Colors much closer than the threshold must map to the same thread."""
        # These two colors are extremely similar (< 2 CIEDE2000 units apart)
        c1 = (40, 40, 40)
        c2 = (42, 42, 42)  # 2-unit RGB shift, tiny ΔE
        result = match_palette(
            [c1, c2],
            strategy="cluster",
            cluster_threshold=5.0,  # very permissive
            catalogue=FIXTURE_CATALOGUE,
        )
        cats = [v[0] for v in result["assignments"].values()]
        assert cats[0] == cats[1], f"Similar colors {c1}/{c2} should cluster to same thread"
        assert len(result["threads_used"]) == 1

    def test_cluster_keeps_distinct_colors_separate(self):
        """Colors far apart (> threshold) must remain in separate clusters."""
        black = (40, 40, 40)
        white = (235, 235, 235)
        result = match_palette(
            [black, white],
            strategy="cluster",
            cluster_threshold=5.0,
            catalogue=FIXTURE_CATALOGUE,
        )
        cats = [v[0] for v in result["assignments"].values()]
        assert cats[0] != cats[1], "Black and white must be in separate clusters"
        assert len(result["threads_used"]) == 2

    def test_cluster_threshold_controls_merging(self):
        """Tight threshold => more clusters; loose threshold => fewer."""
        colors = [(40, 40, 40), (42, 42, 42), (235, 235, 235)]
        tight = match_palette(
            colors, strategy="cluster", cluster_threshold=1.0, catalogue=FIXTURE_CATALOGUE
        )
        loose = match_palette(
            colors, strategy="cluster", cluster_threshold=100.0, catalogue=FIXTURE_CATALOGUE
        )
        assert len(tight["threads_used"]) >= len(loose["threads_used"])

    def test_empty_palette(self):
        result = match_palette([], strategy="greedy", catalogue=FIXTURE_CATALOGUE)
        assert result["assignments"] == {}
        assert result["threads_used"] == []

    def test_threads_used_are_unique(self):
        """threads_used must list each thread at most once."""
        colors = [(40, 40, 40), (40, 40, 40), (41, 41, 41)]
        result = match_palette(colors, strategy="greedy", catalogue=FIXTURE_CATALOGUE)
        cat_numbers = [t[0] for t in result["threads_used"]]
        assert len(cat_numbers) == len(set(cat_numbers)), "threads_used contains duplicates"

    def test_all_strategies_consistent_structure(self):
        """All strategies must return the same dict shape."""
        colors = [(40, 40, 40), (182, 15, 47), (235, 235, 235)]
        for strategy, kwargs in [
            ("greedy", {}),
            ("constrained", {"max_threads": 2}),
            ("cluster", {"cluster_threshold": 20.0}),
        ]:
            result = match_palette(colors, strategy=strategy, catalogue=FIXTURE_CATALOGUE, **kwargs)
            assert "assignments" in result
            assert "threads_used" in result
            assert "strategy" in result
            assert "worst_delta_e" in result
            assert result["strategy"] == strategy


# ---------------------------------------------------------------------------
# Integration tests — full catalogue (skip if absent)
# ---------------------------------------------------------------------------


@catalogue_present
def test_full_catalogue_black_family_at_top():
    """Near-black query against the full catalogue: top result should be dark."""
    results = find_closest_threads((5, 5, 5), top_n=3, algorithm="ciede2000")
    top_lab = _rgb_to_lab(results[0][3])
    assert top_lab[0] < 30, f"Top-1 for near-black should be dark, got L*={top_lab[0]:.1f}"


@catalogue_present
def test_full_catalogue_exact_match_is_top():
    """If the query RGB matches a catalogue entry exactly, it must rank first."""
    import json

    threads = json.loads(CATALOGUE_PATH.read_text())["threads"]
    anchor = threads[0]
    rgb = tuple(anchor["rgb"])
    results = find_closest_threads(rgb, top_n=1, algorithm="ciede2000")
    cat, _name, de, _rgb = results[0]
    assert cat == anchor["catalog_number"], (
        f"Expected {anchor['catalog_number']} at top-1 for exact match, got {cat}"
    )
    assert de < 0.01, f"Exact match ΔE should be ≈ 0, got {de}"


@catalogue_present
@pytest.mark.parametrize("algo", ["ciede2000", "cie76", "rgb", "cmc"])
def test_full_catalogue_all_algorithms_sub_200ms(algo):
    """Per-lookup latency against the full catalogue must be < 200 ms."""
    import time

    color = (186, 155, 80)
    # Warm-up
    find_closest_threads(color, top_n=5, algorithm=algo)
    start = time.perf_counter()
    find_closest_threads(color, top_n=5, algorithm=algo)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 200, f"{algo}: {elapsed_ms:.1f} ms >= 200 ms threshold"


@catalogue_present
def test_palette_greedy_full_catalogue():
    """Greedy palette match should return one thread per input color."""
    colors = [(186, 155, 80), (20, 20, 20), (255, 255, 255), (0, 100, 200)]
    result = match_palette(colors, strategy="greedy")
    assert len(result["assignments"]) == len(colors)
    assert result["worst_delta_e"] >= 0
