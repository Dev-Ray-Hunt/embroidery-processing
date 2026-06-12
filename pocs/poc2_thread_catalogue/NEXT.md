# POC 2 — Next Step: Validation Web UI (Step 3)

Steps 1 (catalogue build) and 2 (color matching engine) are **done**.

```bash
# Rebuild catalogue (~706 threads from GPL sources; 823 with full PDF access)
uv run python -m pocs.poc2_thread_catalogue.src.catalogue
# -> outputs/poc2/madeira_catalogue.json

# Run matching engine tests (44 tests, no data files required for unit layer)
uv run pytest pocs/poc2_thread_catalogue/ -q

# Run benchmark (requires built catalogue)
PYTHONPATH=. uv run python scripts/benchmark_matching.py
# -> outputs/poc2/matching_benchmark.md
```

Headline numbers from Step 2:
- All four algorithms: < 2 ms per search (vs 200 ms bar)
- CIEDE2000 best quality on random colors: mean ΔE₂₀₀₀ = 5.48, p90 = 10.51
- CIEDE2000 vs CMC l:c 2:1 top-1 agreement: 64%

---

## Step 3 tasks

**Validation web UI** — color picker → top-5 swatches with ΔE per algorithm.

1. **FastAPI backend** (`src/api.py` or `src/app.py`):
   - `GET /match?color=rrggbb&algorithm=ciede2000&top_n=5&line=` →
     returns top-N threads as JSON with swatch hex, name, ΔE, catalog number
   - `GET /catalogue?family=red&line=Classic+Rayon+40` → browse endpoint
   - `GET /catalogue/{catalog_number}` → single-thread lookup
   - `GET /health` → liveness check

2. **HTML/JS frontend** (single-file or Jinja2 templates):
   - Browser `<input type="color">` picker + hex input field
   - Top-5 swatches displayed as color blocks: input color side-by-side with
     matched thread color, catalog number, name, ΔE
   - Algorithm toggle (A/B/C/D) to compare results side-by-side
   - Colour-family browser (click "red" → all red threads in catalogue)
   - Search by catalog number or color name

3. **Integration test** (Playwright or httpx):
   - Query a known color, verify the API returns the expected top-1 thread
   - Smoke-test the HTML page renders without JavaScript errors

---

## Step 4 preview (after Step 3)

Physical validation + real-logo testing:
- Photograph 10 spool samples (capture protocol: `src/SPOOL_CAPTURE.md`)
- Run matching against 10 actual Straight Down customer logo color palettes
- Fill out the final algorithm scorecard in FINDINGS.md

---

## Blocked on external input

- **Spool photos** (10 spools, protocol written) — needs Brandon on-site.
- **Isacord↔Madeira equivalence table** — the Isacord RGB palette is downloaded;
  an equivalence table (which Isacord ≈ which Madeira) still needs a source.
- **Full PDF catalogue** — the Madeira shade-card PDFs are network-blocked in this
  sandbox (madeira.com returns 403 "host_not_allowed"); re-fetch manually from a
  machine with full network access and rebuild to get 823 threads instead of 706.
  The one-shot script is in `data/README.md` (section "madeira_sources").
