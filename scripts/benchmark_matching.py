"""Benchmark the POC 2 color matching engine against the full Madeira catalogue.

Measurements (per the POC_2_Thread_Catalogue.md spec):
    1. Delta-E distribution of best matches across 50 random colors per algorithm.
       Each algorithm's top-1 match is evaluated by CIEDE2000 for cross-algorithm
       fairness (the 3.5 JND threshold is a CIEDE2000 concept).
    2. Top-1 agreement rate between all algorithm pairs.
    3. Per-lookup latency against the full catalogue (target: < 200 ms each).

Results are written to outputs/poc2/matching_benchmark.md.
Run with: uv run python scripts/benchmark_matching.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
CATALOGUE_PATH = REPO_ROOT / "outputs" / "poc2" / "madeira_catalogue.json"
OUT_PATH = REPO_ROOT / "outputs" / "poc2" / "matching_benchmark.md"

ALGORITHMS = ["ciede2000", "cie76", "rgb", "cmc"]
ALGORITHM_LABELS = {
    "ciede2000": "A: CIEDE2000",
    "cie76": "B: CIE76",
    "rgb": "C: RGB Euclidean",
    "cmc": "D: CMC l:c 2:1",
}
N_RANDOM = 50
RNG_SEED = 42
LATENCY_REPEATS = 20  # per-algorithm, for stable timing


def generate_random_colors(n: int, seed: int) -> list[tuple[int, int, int]]:
    rng = np.random.default_rng(seed)
    rgb = rng.integers(0, 256, size=(n, 3), dtype=int)
    return [tuple(int(c) for c in row) for row in rgb]


def load_catalogue() -> list[dict]:
    return json.loads(CATALOGUE_PATH.read_text())["threads"]


def ciede2000_of_match(
    query_rgb: tuple[int, int, int],
    match_rgb: tuple[int, int, int],
) -> float:
    """CIEDE2000 between the query and a match returned by any algorithm."""
    import colour

    def rgb_to_lab(rgb):
        srgb = np.array(rgb, dtype=float) / 255.0
        return np.asarray(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(srgb)), dtype=float)

    return float(colour.difference.delta_E_CIE2000(rgb_to_lab(query_rgb), rgb_to_lab(match_rgb)))


def run_benchmark() -> dict:
    import warnings

    warnings.filterwarnings("ignore", message=".*(SciPy|Matplotlib).*")

    from pocs.poc2_thread_catalogue.src.matching import find_closest_threads

    catalogue = load_catalogue()
    n_threads = len(catalogue)
    colors = generate_random_colors(N_RANDOM, RNG_SEED)

    print(f"Catalogue: {n_threads} threads")
    print(f"Random colors: {N_RANDOM} (seed={RNG_SEED})")
    print()

    # -----------------------------------------------------------------------
    # 1 + 2: top-1 matches and CIEDE2000 quality of each algorithm's pick
    # -----------------------------------------------------------------------
    top1: dict[str, list[str]] = {algo: [] for algo in ALGORITHMS}
    # ciede2000 quality = CIEDE2000 of the thread that algorithm chose
    ciede2000_quality: dict[str, list[float]] = {algo: [] for algo in ALGORITHMS}

    for color in colors:
        for algo in ALGORITHMS:
            results = find_closest_threads(color, top_n=1, algorithm=algo, catalogue=catalogue)
            match = results[0]
            top1[algo].append(match[0])  # catalog number
            # Evaluate CIEDE2000 distance of this match to the query
            de2000 = ciede2000_of_match(color, match[3])
            ciede2000_quality[algo].append(de2000)

    # -----------------------------------------------------------------------
    # 3: latency benchmarks
    # -----------------------------------------------------------------------
    bench_color = (186, 155, 80)
    latency_ms: dict[str, float] = {}
    print("Latency benchmarks:")
    for algo in ALGORITHMS:
        # warm-up
        find_closest_threads(bench_color, top_n=5, algorithm=algo, catalogue=catalogue)
        times = []
        for _ in range(LATENCY_REPEATS):
            t0 = time.perf_counter()
            find_closest_threads(bench_color, top_n=5, algorithm=algo, catalogue=catalogue)
            times.append((time.perf_counter() - t0) * 1000)
        latency_ms[algo] = float(np.median(times))
        pass_mark = "✓" if latency_ms[algo] < 200 else "✗"
        print(f"  {ALGORITHM_LABELS[algo]:25s}: {latency_ms[algo]:.2f} ms {pass_mark}")

    print()

    # -----------------------------------------------------------------------
    # Agreement rates (pairwise and all-four)
    # -----------------------------------------------------------------------
    pairs = [(a, b) for i, a in enumerate(ALGORITHMS) for j, b in enumerate(ALGORITHMS) if i < j]
    agreement: dict[tuple[str, str], float] = {}
    for a, b in pairs:
        matches = sum(t1 == t2 for t1, t2 in zip(top1[a], top1[b], strict=True))
        agreement[(a, b)] = matches / N_RANDOM

    all_agree = sum(len({top1[algo][i] for algo in ALGORITHMS}) == 1 for i in range(N_RANDOM))
    all_agree_rate = all_agree / N_RANDOM

    # -----------------------------------------------------------------------
    # Quality stats (CIEDE2000 of each algorithm's pick)
    # -----------------------------------------------------------------------
    stats: dict[str, dict] = {}
    print("CIEDE2000 quality of each algorithm's top-1 pick:")
    for algo in ALGORITHMS:
        de = ciede2000_quality[algo]
        within_3_5 = sum(d < 3.5 for d in de) / len(de) * 100
        stats[algo] = {
            "mean": float(np.mean(de)),
            "median": float(np.median(de)),
            "p90": float(np.percentile(de, 90)),
            "p95": float(np.percentile(de, 95)),
            "max": float(np.max(de)),
            "within_3_5_pct": within_3_5,
        }
        pass_mark = "✓" if within_3_5 >= 90 else "✗"
        print(
            f"  {ALGORITHM_LABELS[algo]:25s}: "
            f"mean={stats[algo]['mean']:.2f}  "
            f"p90={stats[algo]['p90']:.2f}  "
            f"within_3.5={within_3_5:.0f}% {pass_mark}"
        )

    print(f"\nAll-four-algorithm agreement: {all_agree_rate * 100:.1f}%")
    for (a, b), rate in sorted(agreement.items()):
        print(f"  {ALGORITHM_LABELS[a]} vs {ALGORITHM_LABELS[b]}: {rate * 100:.1f}%")

    return {
        "n_threads": n_threads,
        "n_random": N_RANDOM,
        "rng_seed": RNG_SEED,
        "stats": stats,
        "latency_ms": latency_ms,
        "agreement": {f"{a}_vs_{b}": v for (a, b), v in agreement.items()},
        "all_agree_rate": all_agree_rate,
        "top1": top1,
        "ciede2000_quality": ciede2000_quality,
    }


def write_markdown(result: dict) -> None:
    stats = result["stats"]
    latency = result["latency_ms"]
    agreement = result["agreement"]

    lines = [
        "# POC 2 — Color Matching Engine Benchmark",
        "",
        f"Catalogue: **{result['n_threads']} threads**"
        + (
            ""
            if result["n_threads"] >= 823
            else " (partial build — Ink/Stitch GPL sources only; full catalogue is 823 threads)"
        )
        + ".",
        "",
        f"Random colors: **{result['n_random']}** (RNG seed {result['rng_seed']}).",
        "",
        "---",
        "",
        "## CIEDE2000 Quality of Each Algorithm's Top-1 Match",
        "",
        "Each algorithm selects its top-1 thread using its own metric; the table shows the",
        "**CIEDE2000 distance** of that match to the query — a fair cross-algorithm comparison.",
        "Pass criterion (POC spec): ≥ 90% of colors within ΔE₂₀₀₀ < 3.5.",
        "",
        "| Algorithm | Mean | Median | p90 | p95 | Max | % < 3.5 |",
        "|-----------|------|--------|-----|-----|-----|---------|",
    ]
    for algo in ALGORITHMS:
        s = stats[algo]
        label = ALGORITHM_LABELS[algo]
        pass_mark = "✓" if s["within_3_5_pct"] >= 90 else "✗"
        lines.append(
            f"| {label} "
            f"| {s['mean']:.2f} "
            f"| {s['median']:.2f} "
            f"| {s['p90']:.2f} "
            f"| {s['p95']:.2f} "
            f"| {s['max']:.2f} "
            f"| {s['within_3_5_pct']:.0f}% {pass_mark} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Per-Lookup Latency",
        "",
        f"Median over {LATENCY_REPEATS} repeats, single color vs full catalogue.  "
        "Target: < 200 ms each.",
        "",
        "| Algorithm | Median latency (ms) | Pass? |",
        "|-----------|---------------------|-------|",
    ]
    for algo in ALGORITHMS:
        ms = latency[algo]
        mark = "✓" if ms < 200 else "✗"
        lines.append(f"| {ALGORITHM_LABELS[algo]} | {ms:.2f} | {mark} |")

    lines += [
        "",
        "---",
        "",
        "## Algorithm Agreement (Top-1)",
        "",
        f"All four algorithms agree on top-1: **{result['all_agree_rate'] * 100:.1f}%** of colors.",
        "",
        "| Pair | Agreement rate |",
        "|------|---------------|",
    ]
    for key, rate in sorted(agreement.items()):
        a, b = key.split("_vs_")
        lines.append(f"| {ALGORITHM_LABELS[a]} vs {ALGORITHM_LABELS[b]} | {rate * 100:.1f}% |")

    lines += [
        "",
        "---",
        "",
        "## Notes",
        "",
        "- Latency varies with hardware; the < 200 ms target leaves ample headroom either way.",
        "- CMC configured for textile acceptability (l=2, c=1).",
        "- Random test colors include values that likely have no close thread match "
        "(e.g. saturated neons); real-logo colors would score higher.",
        "- Spool-photo validation and real-logo tests remain for Step 4.",
    ]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n")
    print(f"\nBenchmark written to {OUT_PATH}")


def main() -> int:
    import warnings

    warnings.filterwarnings("ignore", message=".*(SciPy|Matplotlib).*")

    if not CATALOGUE_PATH.exists():
        print(f"ERROR: {CATALOGUE_PATH} not found.")
        print("Run: uv run python -m pocs.poc2_thread_catalogue.src.catalogue")
        return 1

    result = run_benchmark()
    write_markdown(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
