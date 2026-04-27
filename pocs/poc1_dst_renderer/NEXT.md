# POC 1 — Next Step: DST Parsing Foundation

From [POC_1_DST_Renderer.md](../../POC_1_DST_Renderer.md), Step 1: build the DST parsing utility that all 5 renderers will consume. Do this *before* any rendering work — same parsed JSON, five renderers.

## Tasks

1. **Acquire test DSTs** — drop into `../../data/sample_dsts/` (gitignored).

   **Tier 1 (DONE 2026-04-27):** 3 publicly-licensed (zlib) DSTs from Embroidermodder/Embroidermodder. All under 5k stitches. See [`data/README.md`](../../data/README.md) for filenames, stitch counts, sources, and a one-shot re-fetch script.

   **Tier 2 (10k–20k stitches) and Tier 3 (30k+ stitches): DEFERRED.** No public-domain DST corpus exists at these stitch counts (researched 2026-04-27 across Embroidermodder, libembroidery, EmbroidePy/samples, Inkstitch, pyembroidery, p5.embroider, StitchView, stitchcode). Brandon is sourcing larger files from the Straight Down team; they'll land in `data/sample_dsts/` (gitignored) when supplied. Parser work below should not assume any specific Tier 2/3 file exists yet but should be tested against them once they arrive.

2. **Write the parser** (`src/dst_parser.py`) — given a DST file path, return a structured representation of:
   - stitch coordinates (list of `(x, y, command)` tuples or equivalent)
   - color-change events (indices into the stitch list where threads change)
   - jump stitches (separated from normal stitches; renderers may skip them)
   - metadata (total stitch count, bounding box / extents, color count)

3. **Define the canonical JSON schema** all 5 renderers will consume. Keep it small and obvious. Document in `src/SCHEMA.md`.

4. **Validation** — internal-consistency checks only. No Wilcom ground truth available (architectural isolation). At minimum:
   - parsed stitch count == `pyembroidery`'s reported count
   - bounding box matches `pyembroidery`'s extents
   - round-trip parse → JSON → reparse is stable

5. **Tests** in `tests/test_dst_parser.py` — assert the above against the Tier 1 DSTs (and Tier 2/3 once supplied).

## Definition of done

- `uv run python -m pocs.poc1_dst_renderer.src.dst_parser <path-to-dst>` prints parsed JSON for any of the Tier 1 samples.
- `uv run pytest pocs/poc1_dst_renderer/tests/` passes.
- `src/SCHEMA.md` documents the JSON shape clearly enough that the next session can start writing renderer A (pyembroidery PNG baseline) or B (Pillow 2D) against it without re-reading the parser code.
