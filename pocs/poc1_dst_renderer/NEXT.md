# POC 1 — Next Step: DST Parsing Foundation

From [POC_1_DST_Renderer.md](../../POC_1_DST_Renderer.md), Step 1: build the DST parsing utility that all 5 renderers will consume. Do this *before* any rendering work — same parsed JSON, five renderers.

## Tasks

1. **Acquire 3 public sample DSTs** — drop into `../../data/sample_dsts/` (gitignored). Need:
   - simple text-only logo (< 5k stitches)
   - multi-color logo with fills (10k–20k stitches)
   - complex detailed design (30k+ stitches)

   Sources:
   - [`pyembroidery` test corpus](https://github.com/EmbroidePy/pyembroidery/tree/main/test/assets)
   - other public-domain embroidery libraries (record source URL + license in `data/README.md`)

   **No Straight Down production DSTs.** This project is source-isolated.

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

5. **Tests** in `tests/test_dst_parser.py` — assert the above against the 3 sample DSTs.

## Definition of done

- `uv run python -m pocs.poc1_dst_renderer.src.dst_parser <path-to-dst>` prints parsed JSON for any of the 3 samples.
- `uv run pytest pocs/poc1_dst_renderer/tests/` passes.
- `src/SCHEMA.md` documents the JSON shape clearly enough that the next session can start writing renderer A (pyembroidery PNG baseline) or B (Pillow 2D) against it without re-reading the parser code.
