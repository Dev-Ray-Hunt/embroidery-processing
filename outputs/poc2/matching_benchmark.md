# POC 2 — Color Matching Engine Benchmark

Catalogue: **706 threads** (Ink/Stitch GPL sources; Madeira PDFs network-blocked in sandbox — full 823-thread catalogue expected in production).

Random colors: **50** (RNG seed 42).

---

## CIEDE2000 Quality of Each Algorithm's Top-1 Match

Each algorithm selects its top-1 thread using its own metric; the table shows the
**CIEDE2000 distance** of that match to the query — a fair cross-algorithm comparison.
Pass criterion (POC spec): ≥ 90% of colors within ΔE₂₀₀₀ < 3.5.

| Algorithm | Mean | Median | p90 | p95 | Max | % < 3.5 |
|-----------|------|--------|-----|-----|-----|---------|
| A: CIEDE2000 | 5.48 | 4.33 | 10.51 | 12.32 | 15.12 | 24% ✗ |
| B: CIE76 | 6.64 | 5.02 | 14.34 | 16.50 | 18.72 | 22% ✗ |
| C: RGB Euclidean | 7.20 | 6.04 | 13.70 | 14.91 | 19.35 | 16% ✗ |
| D: CMC l:c 2:1 | 6.51 | 4.50 | 13.64 | 16.21 | 17.84 | 22% ✗ |

---

## Per-Lookup Latency

Median over 20 repeats, single color vs full catalogue.  Target: < 200 ms each.

| Algorithm | Median latency (ms) | Pass? |
|-----------|---------------------|-------|
| A: CIEDE2000 | 1.25 | ✓ |
| B: CIE76 | 0.76 | ✓ |
| C: RGB Euclidean | 0.70 | ✓ |
| D: CMC l:c 2:1 | 0.89 | ✓ |

---

## Algorithm Agreement (Top-1)

All four algorithms agree on top-1: **24.0%** of colors.

| Pair | Agreement rate |
|------|---------------|
| B: CIE76 vs D: CMC l:c 2:1 | 74.0% |
| B: CIE76 vs C: RGB Euclidean | 34.0% |
| A: CIEDE2000 vs B: CIE76 | 50.0% |
| A: CIEDE2000 vs D: CMC l:c 2:1 | 64.0% |
| A: CIEDE2000 vs C: RGB Euclidean | 36.0% |
| C: RGB Euclidean vs D: CMC l:c 2:1 | 30.0% |

---

## Notes

- Sandbox network policy blocked madeira.com/madeirausa.com (HTTP 403); catalogue built from Ink/Stitch GPL sources only (706 threads vs 823 expected).
- Latency measured on a remote cloud container; times will differ on local hardware.
- CMC configured for textile acceptability (l=2, c=1).
- Random test colors include values that likely have no close thread match (e.g. saturated neons); real-logo colors would score higher.
- Spool-photo validation and real-logo tests remain for Step 4.
