# POC 2 — Next Step: Color Matching Engine (Step 2)

Step 1 (catalogue build) is **done** — 823 threads (391 Classic Rayon 40 +
432 Polyneon 40) from 6 reconciled sources. Build it any time:

```bash
uv run python -m pocs.poc2_thread_catalogue.src.catalogue
# -> outputs/poc2/madeira_catalogue.json   (schema: src/SCHEMA.md)
```

Sources, provenance and the re-fetch script live in `data/README.md`.
51 entries are conflict-flagged (sources disagree, ΔE76 > 18) — they are the
priority list for the physical spool validation (`src/SPOOL_CAPTURE.md`,
ready for when Brandon is on-site).

## Step 2 tasks (from POC_2_Thread_Catalogue.md)

1. **Matching algorithms bake-off** — implement all four:
   - A: CIEDE2000 (`colour-science` has `colour.difference.delta_E_CIE2000`)
   - B: CIE76 (Euclidean in Lab — already in `catalogue.delta_e76`)
   - C: Euclidean in RGB (the floor)
   - D: CMC l:c 2:1 (textile standard; `colour` implements it)
2. **`find_closest_threads(color, top_n, algorithm, line=None)`** over the
   catalogue; accept RGB tuples and hex.
3. **`match_palette(design_colors, ...)`** with the three strategies
   (greedy / constrained-N / perceptual clustering).
4. **Unit tests** with known color pairs (published CIEDE2000 test vectors
   exist — Sharma et al. 2005 dataset) + ranking sanity checks.
5. **Measurements**: 50-random-color Delta-E distribution per algorithm,
   algorithm agreement rate, matching speed (<200ms bar is for search).

## Step 3 preview (after Step 2)

Validation web UI — color picker → top-5 swatches with ΔE per algorithm.
Note the Stitch Proofer (webapp/) is the natural future home: its per-block
color pickers should eventually offer "nearest Madeira threads" from this
catalogue.

## Blocked on external input

- Spool photos (10 spools, protocol written) — needs Brandon on-site.
- Isacord↔Madeira equivalence list for the Task 2 cross-check — the Isacord
  RGB palette is downloaded; an equivalence table (which Isacord ≈ which
  Madeira) still needs a source.
