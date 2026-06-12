# POC 2 — Next Step: Physical Validation (Step 4)

Steps 1 (catalogue build), 2 (color matching engine), and 3 (validation web UI)
are **done**.

```bash
# Rebuild catalogue (full 823 threads with network access; 706 from GPL sources only)
uv run python -m pocs.poc2_thread_catalogue.src.catalogue
# -> outputs/poc2/madeira_catalogue.json

# Run the validation web UI
uv run uvicorn pocs.poc2_thread_catalogue.src.api:app --reload
# -> open http://127.0.0.1:8000/

# Run tests (71 = pure math + unit + API + browser smoke; unit layer needs no data files)
uv run pytest pocs/poc2_thread_catalogue/ -q

# Run benchmark (requires built catalogue)
PYTHONPATH=. uv run python scripts/benchmark_matching.py
# -> outputs/poc2/matching_benchmark.md
```

What the UI gives you (Step 3 deliverable):
- Color picker / hex input → top-5 thread swatches side-by-side with the input
  color, per algorithm (A/B/C/D toggle or all four at once), with ΔE badges.
- Catalogue browser: color-family chips, line filter, search by catalog number
  or name. Clicking any thread tile runs a match on its color.

---

## Step 4 tasks — physical validation + real-logo testing

1. **Spool photos** (needs Brandon on-site): photograph 10 spool samples per
   the capture protocol in `src/SPOOL_CAPTURE.md`. The 51 conflict-flagged
   catalogue entries are the priority list.
2. **Real-logo palettes**: collect ~10 actual Straight Down customer logo
   color palettes; run them through `/api/match` (or `match_palette`) and
   judge the top-1 picks by eye in the validation UI.
3. **Scorecard**: fill out the final algorithm scorecard in FINDINGS.md and
   make the CIEDE2000-vs-CMC call with physical evidence.

---

## Blocked on external input

- **Spool photos** (10 spools, protocol written) — needs Brandon on-site.
- **Customer logo palettes** — needs Brandon to pick ~10 low-sensitivity
  customers and export their logo colors.
- **Isacord↔Madeira equivalence table** — the Isacord RGB palette is downloaded;
  an equivalence table (which Isacord ≈ which Madeira) still needs a source.
