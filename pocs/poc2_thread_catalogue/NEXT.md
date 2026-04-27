# POC 2 — Next Step: Madeira Data Collection & Catalogue Build

From [POC_2_Thread_Catalogue.md](../../POC_2_Thread_Catalogue.md). Catalogue first; matching algorithms come once the data is solid.

## Tasks

1. **Identify and download non-Wilcom Madeira sources** into `../../data/madeira_sources/` (gitignored):
   - Madeira Metro chart (RGB + catalog number reference)
   - EZ Stitch's Madeira data (cross-reference)
   - Madeira's own digital color chart (PDF or web data)
   - Isacord RGB PDF as a parallel cross-reference (best-documented thread brand, useful for sanity-checking method)

   For each source, record source URL, retrieval date, and license/usage status in `data/README.md` at repo root.

2. **Parse each source** into a normalized intermediate (CSV or JSON) with: catalog number, color name, RGB, line/family, source.

3. **Merge & reconcile** — flag conflicts (same catalog # → different RGB across sources) and decide a resolution rule (e.g., majority-vote, prefer Madeira-official). Document the rule.

4. **Convert RGB → CIELAB** under D65 illuminant. Use a well-tested library (e.g., `colour-science` — add it to `pyproject.toml` when this task starts).

5. **Assign color families** — automated (e.g., HSL hue bucketing) or manual review. Family taxonomy should be coarse enough for editor browse-by-family (red/orange/yellow/green/blue/purple/pink/brown/neutral/black/white/metallic).

6. **Emit `madeira_catalogue.json`** to `outputs/poc2/madeira_catalogue.json` with the agreed schema. Target ≥ 200 entries covering Classic Rayon 40 + Polyneon.

7. **Spool photo validation** — defer the on-site task. Document the capture protocol in `src/SPOOL_CAPTURE.md` (lighting, white-balance reference, distance, file naming) so it's ready when Brandon can do it in person. Photos go to `data/madeira_sources/spool_photos/` when captured.

## Definition of done

- `outputs/poc2/madeira_catalogue.json` exists with ≥ 200 entries, each with `catalog_number`, `name`, `rgb`, `lab`, `family`, `line`, `source`.
- Schema is documented in `src/SCHEMA.md`.
- `uv run pytest pocs/poc2_thread_catalogue/tests/` passes (smoke tests: schema validity, no duplicate catalog #s, all RGB values in [0, 255], LAB conversion round-trip within tolerance).
- Spool capture protocol written and ready.

## Parallelism note

This work has zero dependencies on POC 1. Run alongside POC 1 Step 1 in separate sessions.
