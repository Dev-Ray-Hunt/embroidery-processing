"""Color matching engine for the Madeira thread catalogue (POC 2 Step 2).

Four-algorithm bake-off:
    "ciede2000" — CIEDE2000 in CIELAB  (current industry standard)
    "cie76"     — CIE76 / Euclidean in CIELAB  (simple, fast)
    "rgb"       — Euclidean in sRGB  (the floor / baseline)
    "cmc"       — CMC l:c 2:1 in CIELAB  (textile industry standard)

Do NOT import cairo from this module.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOGUE_PATH = REPO_ROOT / "outputs" / "poc2" / "madeira_catalogue.json"

Algorithm = Literal["ciede2000", "cie76", "rgb", "cmc"]
# (catalog_number, color_name, delta_e, rgb)
MatchResult = tuple[str, str | None, float, tuple[int, int, int]]

# ---------------------------------------------------------------------------
# Color conversion helpers
# ---------------------------------------------------------------------------


def _parse_color(color: tuple[int, int, int] | str) -> tuple[int, int, int]:
    """Accept (R, G, B) 0-255 tuple or '#rrggbb' / 'rrggbb' hex string."""
    if isinstance(color, str):
        h = color.lstrip("#")
        if len(h) != 6:
            raise ValueError(f"Expected 6-digit hex, got {color!r}")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    r, g, b = color
    return (int(r), int(g), int(b))


def _rgb_to_lab(rgb: tuple[int, int, int]) -> np.ndarray:
    """sRGB (0-255) -> CIELAB [L, a*, b*] under D65 illuminant."""
    import colour

    srgb = np.array(rgb, dtype=float) / 255.0
    return np.asarray(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(srgb)), dtype=float)


def _lab_to_approx_rgb(lab: np.ndarray) -> np.ndarray:
    """Approximate CIELAB -> sRGB (0-255).  Used only when the RGB
    algorithm is requested with a Lab centroid (cluster strategy)."""
    import colour

    xyz = colour.Lab_to_XYZ(lab)
    return np.clip(colour.XYZ_to_sRGB(xyz), 0.0, 1.0) * 255.0


# ---------------------------------------------------------------------------
# Catalogue loading & vectorised index
# ---------------------------------------------------------------------------


class _Index:
    """Pre-computed per-algorithm numpy arrays.  Build once, query many times."""

    def __init__(self, threads: list[dict]) -> None:
        self.threads = threads
        self.labs = np.array([t["lab"] for t in threads], dtype=float)  # (N, 3)
        self.rgbs = np.array([t["rgb"] for t in threads], dtype=float)  # (N, 3)

    def distances(
        self,
        query_lab: np.ndarray,
        query_rgb: np.ndarray,
        algorithm: Algorithm,
    ) -> np.ndarray:
        """Return an (N,) array of delta-E from the query to every thread."""
        import colour

        if algorithm == "cie76":
            return np.linalg.norm(self.labs - query_lab, axis=1)

        if algorithm == "rgb":
            return np.linalg.norm(self.rgbs - query_rgb, axis=1)

        # For CIEDE2000 and CMC, broadcast query_lab to shape (N, 3)
        lab1 = np.broadcast_to(query_lab, self.labs.shape).copy()

        if algorithm == "ciede2000":
            return colour.difference.delta_E_CIE2000(lab1, self.labs)

        if algorithm == "cmc":
            return colour.difference.delta_E_CMC(lab1, self.labs, l=2, c=1)

        raise ValueError(f"Unknown algorithm: {algorithm!r}")


_catalogue_cache: list[dict] | None = None


def _load_catalogue() -> list[dict]:
    global _catalogue_cache
    if _catalogue_cache is None:
        _catalogue_cache = json.loads(CATALOGUE_PATH.read_text())["threads"]
    return _catalogue_cache


def _make_index(threads: list[dict] | None = None, line: str | None = None) -> _Index:
    if threads is None:
        threads = _load_catalogue()
    if line is not None:
        threads = [t for t in threads if t["line"] == line]
    if not threads:
        raise ValueError(f"No threads found (line filter: {line!r})")
    return _Index(threads)


# ---------------------------------------------------------------------------
# Primary public API
# ---------------------------------------------------------------------------


def find_closest_threads(
    color: tuple[int, int, int] | str,
    top_n: int = 5,
    algorithm: Algorithm = "ciede2000",
    line: str | None = None,
    *,
    catalogue: list[dict] | None = None,
) -> list[MatchResult]:
    """Return the *top_n* closest Madeira threads sorted by ascending delta-E.

    Parameters
    ----------
    color:
        Input color as ``(R, G, B)`` tuple (0-255) or ``"#rrggbb"`` hex string.
    top_n:
        Number of results to return.
    algorithm:
        ``"ciede2000"`` | ``"cie76"`` | ``"rgb"`` | ``"cmc"``
    line:
        Optional line filter — ``"Classic Rayon 40"`` or ``"Polyneon 40"``.
    catalogue:
        Override the default loaded catalogue (pass a small inline list for
        unit tests to avoid depending on the gitignored outputs/ file).

    Returns
    -------
    list of ``(catalog_number, color_name, delta_e, rgb)`` tuples sorted
    ascending by *delta_e*.
    """
    rgb = _parse_color(color)
    lab = _rgb_to_lab(rgb)
    idx = _make_index(catalogue, line)
    dists = idx.distances(lab, np.array(rgb, dtype=float), algorithm)
    order = np.argsort(dists)[:top_n]
    return [
        (
            idx.threads[i]["catalog_number"],
            idx.threads[i].get("color_name"),
            float(dists[i]),
            tuple(int(c) for c in idx.threads[i]["rgb"]),
        )
        for i in order
    ]


def match_palette(
    design_colors: list[tuple[int, int, int] | str],
    algorithm: Algorithm = "ciede2000",
    strategy: Literal["greedy", "constrained", "cluster"] = "greedy",
    max_threads: int | None = None,
    cluster_threshold: float = 10.0,
    line: str | None = None,
    *,
    catalogue: list[dict] | None = None,
) -> dict:
    """Match a multi-color design palette to Madeira threads.

    Parameters
    ----------
    design_colors:
        List of input colors (RGB tuples or hex strings).
    algorithm:
        Delta-E metric to use for all distance calculations.
    strategy:
        ``"greedy"``      — match each design color independently (fastest,
                            may return many threads).
        ``"constrained"`` — limit total unique threads to *max_threads*,
                            minimising worst-case delta-E (greedy k-center).
        ``"cluster"``     — group design colors whose CIEDE2000 pairwise
                            distance is below *cluster_threshold*, then
                            assign one thread per cluster.
    max_threads:
        Required for ``"constrained"``; ignored otherwise.
    cluster_threshold:
        CIEDE2000 distance below which two design colors are merged into
        the same cluster (``"cluster"`` strategy only).
    catalogue:
        Override catalogue for unit tests.

    Returns
    -------
    dict with keys:

    * ``"assignments"``   — ``{color_repr: MatchResult}``
    * ``"threads_used"``  — unique ``MatchResult`` list
    * ``"strategy"``      — strategy name
    * ``"worst_delta_e"`` — max delta-E across all assignments
    """
    if not design_colors:
        return {"assignments": {}, "threads_used": [], "strategy": strategy, "worst_delta_e": 0.0}

    colors = [_parse_color(c) for c in design_colors]
    idx = _make_index(catalogue, line)

    if strategy == "greedy":
        assignments = _greedy(colors, idx, algorithm)
    elif strategy == "constrained":
        if max_threads is None:
            raise ValueError("max_threads is required for 'constrained' strategy")
        assignments = _constrained(colors, idx, algorithm, max_threads)
    elif strategy == "cluster":
        assignments = _cluster(colors, idx, algorithm, cluster_threshold)
    else:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    color_reprs = [
        c if isinstance(c, str) else "#{:02x}{:02x}{:02x}".format(*c) for c in design_colors
    ]
    assignment_map = {color_reprs[i]: assignments[i] for i in range(len(colors))}
    # Deduplicate by catalog_number, keeping the first occurrence
    seen: set[str] = set()
    unique: list[MatchResult] = []
    for a in assignments:
        if a[0] not in seen:
            seen.add(a[0])
            unique.append(a)

    return {
        "assignments": assignment_map,
        "threads_used": unique,
        "strategy": strategy,
        "worst_delta_e": max(a[2] for a in assignments),
    }


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------


def _greedy(
    colors: list[tuple[int, int, int]],
    idx: _Index,
    algorithm: Algorithm,
) -> list[MatchResult]:
    results: list[MatchResult] = []
    for rgb in colors:
        lab = _rgb_to_lab(rgb)
        dists = idx.distances(lab, np.array(rgb, dtype=float), algorithm)
        i = int(np.argmin(dists))
        results.append(
            (
                idx.threads[i]["catalog_number"],
                idx.threads[i].get("color_name"),
                float(dists[i]),
                tuple(int(c) for c in idx.threads[i]["rgb"]),
            )
        )
    return results


def _constrained(
    colors: list[tuple[int, int, int]],
    idx: _Index,
    algorithm: Algorithm,
    max_threads: int,
) -> list[MatchResult]:
    """Greedy k-center heuristic: iteratively select the catalogue thread that
    minimises the current maximum unmet delta-E.

    Complexity: O(max_threads * N_catalogue * N_colors).
    """
    n_colors = len(colors)
    n_catalogue = len(idx.threads)
    k = min(max_threads, n_catalogue, n_colors)

    # Pre-compute full delta-E matrix: rows = design colors, cols = catalogue
    de_matrix = np.zeros((n_colors, n_catalogue), dtype=float)
    for ci, rgb in enumerate(colors):
        lab = _rgb_to_lab(rgb)
        de_matrix[ci] = idx.distances(lab, np.array(rgb, dtype=float), algorithm)

    selected: list[int] = []  # indices into idx.threads
    best_so_far = np.full(n_colors, np.inf)  # best delta-E per color given selected threads

    for _ in range(k):
        # new_best[c, t] = min(best_so_far[c], de_matrix[c, t])
        new_best = np.minimum(best_so_far[:, None], de_matrix)  # (n_colors, n_catalogue)
        new_worst = new_best.max(axis=0)  # (n_catalogue,) — worst case if t is added
        t_star = int(np.argmin(new_worst))
        selected.append(t_star)
        best_so_far = np.minimum(best_so_far, de_matrix[:, t_star])

    # Assign each design color to its closest selected thread
    selected_de = de_matrix[:, selected]  # (n_colors, k)
    best_idx = np.argmin(selected_de, axis=1)  # (n_colors,)

    return [
        (
            idx.threads[selected[int(best_idx[ci])]]["catalog_number"],
            idx.threads[selected[int(best_idx[ci])]].get("color_name"),
            float(de_matrix[ci, selected[int(best_idx[ci])]]),
            tuple(int(c) for c in idx.threads[selected[int(best_idx[ci])]]["rgb"]),
        )
        for ci in range(n_colors)
    ]


def _cluster(
    colors: list[tuple[int, int, int]],
    idx: _Index,
    algorithm: Algorithm,
    threshold: float,
) -> list[MatchResult]:
    """Single-linkage agglomerative clustering on design colors using CIEDE2000
    pairwise distance; one thread matched per cluster.

    Cluster centroids are computed in Lab space; the chosen algorithm then
    matches each centroid to the catalogue.
    """
    import colour

    n = len(colors)
    labs = np.array([_rgb_to_lab(rgb) for rgb in colors], dtype=float)

    # Pairwise CIEDE2000 between design colors
    pairwise = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            d = float(colour.difference.delta_E_CIE2000(labs[i], labs[j]))
            pairwise[i, j] = pairwise[j, i] = d

    # Union-find for single-linkage clustering
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    for i in range(n):
        for j in range(i + 1, n):
            if pairwise[i, j] < threshold:
                union(i, j)

    # Group indices by cluster root
    clusters: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        clusters.setdefault(root, []).append(i)

    # Match each cluster's Lab centroid to the catalogue
    cluster_match: dict[int, MatchResult] = {}
    for root, members in clusters.items():
        centroid = labs[members].mean(axis=0)
        approx_rgb = _lab_to_approx_rgb(centroid)
        dists = idx.distances(centroid, approx_rgb, algorithm)
        best_i = int(np.argmin(dists))
        cluster_match[root] = (
            idx.threads[best_i]["catalog_number"],
            idx.threads[best_i].get("color_name"),
            float(dists[best_i]),
            tuple(int(c) for c in idx.threads[best_i]["rgb"]),
        )

    return [cluster_match[find(i)] for i in range(n)]
