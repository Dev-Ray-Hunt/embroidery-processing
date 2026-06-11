# POC 1: DST Renderer — Findings

> Status 2026-06-10: all five renderers implemented and machine-verified.
> Remaining: Brandon's subjective quality pass (gallery + live UI) and the
> stitched-sample ground-truth photo comparison.

## What we built

All five bake-off approaches, all consuming the canonical parser
(`src/dst_parser.py` → `src/SCHEMA.md`), all supporting the three POC fabrics
(white/black/navy, solid colors) and the shared 20-color default palette
(`shared/design_colors.py` — placeholder until POC 2 supplies real Madeira
colors; every renderer takes a palette override).

- **A. pyembroidery PNG** (`src/renderers/a_pyembroidery.py`) — the library's
  built-in writer, zero custom code. *Deviations:* pyembroidery picks its own
  random thread colors (no palette control) and has no background support —
  the harness composites its transparent output over the fabric color.
- **B. Pillow 2D + angle shading** (`src/renderers/b_pillow.py`) — thick
  round lines, brightness modulated by stitch angle (cos², horizontal bright /
  vertical dark), 2× supersample + Lanczos. Fill direction is visibly encoded
  — verified programmatically (horizontal runs measure ≥15% brighter).
- **C. Cairo antialiased vector** (`src/renderers/c_cairo.py`) — round caps,
  best-quality AA, translucent body pass (α 0.85) so dense fills accumulate,
  thin lighter sheen stroke per stitch. Could also emit SVG/PDF.
- **D. HTML5 Canvas** (`web/static/renderer_d.js`) — browser-side, batched
  per color block. Wheel zoom about the cursor, drag pan, and
  **hover-to-highlight a color block** (picking-canvas hit test) — a direct
  rehearsal of POC 3's color-up interaction. No shading (flat color).
- **E. Three.js 2.5D** (`web/static/renderer_e.js`, vendored three.js r180) —
  instanced 3D boxes per stitch on a fabric plane, monotonic height stacking
  (later thread sits on top), per-stitch height jitter, PBR lighting. Zoom,
  pan, shift-drag tilt. *Deviation:* standard PBR instead of a custom
  Kajiya-Kay anisotropic shader — listed under future work.

## What we measured

Full table: `uv run python scripts/benchmark.py` → `outputs/benchmark_results.md`.
Headline numbers (warm; D/E browser numbers under **software** WebGL —
real-GPU is faster):

| Design (stitches) | A | B | C | D draw | E draw |
|---|---|---|---|---|---|
| star.dst (2,550) | 102 ms | 41 ms | 60 ms | <1 ms | 4 ms |
| 000001055-007 (20,623) | 576 ms | 114 ms | 269 ms | 1 ms | 5 ms |
| 000000813-092 (63,710) | 1,997 ms | 210 ms | 419 ms | 4 ms | 15 ms |

- Every renderer is far inside the POC's **< 10 s @ 20k stitches** bar; all
  but A also beat the **< 2 s** "excellent" bar even at 63k stitches.
- D/E cold (fetch JSON + build geometry): 0.5 s / 0.9 s at 63k stitches.
- Output sizes: A 8–202 KB, B 91–794 KB, C 81–1,335 KB per PNG.
- No degradation point found inside the corpus: the 63k-stitch design is the
  largest available and nothing choked. A 100k+ test needs a bigger DST.
- Visual side-by-side vs. stitched photo: **blocked** — no ground-truth photo
  supplied yet (the one remaining item from the team file request).
- Gallery (105 images: 5 renderers × 7 designs × 3 fabrics):
  `uv run python scripts/build_gallery.py` → `open outputs/gallery/index.html`.

## Scorecard

**Provisional, builder-estimated.** R/S/F are largely objective (measured
above); **Q is a placeholder pending Brandon's gallery review and the
stitched-photo comparison**, which may move any Q score ±1 or more.
Formula `(R × 4) + (Q × 3) + (S × 2) + (F × 1)`, max 50, MVP threshold 30.

| Renderer | R | Q* | S | F | Weighted |
|----------|---|---|---|---|----------|
| A. pyembroidery PNG | 5 | 2 | 3 | 1 | 33 |
| B. Pillow 2D | 5 | 4 | 5 | 3 | 45 |
| C. Cairo 2D | 5 | 4 | 4 | 3 | 43 |
| D. HTML5 Canvas | 4 | 3 | 5 | 5 | 40 |
| E. WebGL/Three.js | 3 | 4 | 4 | 5 | 37 |

Reasoning: A loses Q (flat, random colors, no fabric) and F (nothing
configurable). B is the speed/control sweet spot. C looks smoothest but runs
~2× B with a slightly washed translucent look. D is the fastest and the only
one with the POC 3 interaction, but flat-color (no thread shading). E is the
most realistic-feeling (depth + lighting) and the most complex/fragile
(WebGL dependency, most code).

## Pass/fail criteria

| Criterion | Status |
|---|---|
| ≥1 approach a non-technical person recognizes as embroidery | **Brandon to judge** (gallery ready; builder's view: B, C, E qualify) |
| < 10 s for a 20k-stitch design | **PASS** — worst is A at 0.58 s |
| Thread colors match Madeira | **Deferred to POC 2 by design** — placeholder palette; override hook in place |
| Fill direction visible in preview | **PASS for B** (machine-verified) and **E** (geometric); C partial (sheen, not angle-dependent); D no |
| ≥3 fabric backgrounds | **PASS** — white/black/navy across all five (A via composite) |
| Wilcom DSTs parse, counts match | **PASS** against pyembroidery (no Wilcom ground truth by architectural isolation); 7/7 files parse |

## What we learned

- **DST y-axis is screen-oriented in pyembroidery** (+y down) — verified
  empirically (IoU 0.95 vs 0.41 flipped against renderer A).
- **Thread is cut at color changes.** All three custom geometry builders
  initially drew a connector segment into each new color block; the synthetic
  test fixtures caught it. Renderers must reset the pen at COLOR_CHANGE.
- **Stitch order is a z-order.** In E, drawing all stitches at one height
  z-fights badly (lettering interleaved with the fill under it). Raising z
  monotonically with stitch index — which is physically true of real thread —
  fixed it outright.
- **2D + angle shading gets surprisingly far.** B's cheap cos² trick reads as
  thread sheen at a glance; E's edge over it is depth at high zoom, not
  legibility.
- pyembroidery's writer (A) is genuinely just a floor: no colors, no
  background, slowest at scale. Its value is validation, not output.
- The Kajiya-Kay shader was not needed to get a credible 2.5D look — oriented
  instanced geometry under a directional light produces angle-dependent sheen
  "for free." The custom shader remains the obvious next quality step for E.

## Recommendation if shipping for real (draft — Brandon decides)

- **Primary (customer proof images, server-side): B**, with C the fallback if
  the smoother AA look wins the eye test. Both pure-Python, fast, palette-
  ready for POC 2/3. All five crossed the MVP threshold (30), so this is a
  choice among viable options, not a rescue.
- **Secondary (interactive, POC 3 editor): D** — fastest, simplest, and its
  hover-highlight is already the editor's core gesture. **E** is the premium
  customer-facing view if the 2.5D look earns it on a real GPU; revisit after
  the eye test.

## Open questions / followups

- Stitched-sample ground-truth photo (team request, outstanding) — the only
  way to score visual fidelity honestly.
- Kajiya-Kay anisotropic thread shader for E; GPU (non-SwiftShader) perf pass.
- Procedural fabric weave texture (strictly-solids was a deliberate scope cut).
- Real Madeira palette plumb-through once POC 2 lands.
- 100k+ stitch stress test if a large-enough DST surfaces.

## How to reproduce

```bash
uv run pytest pocs/poc1_dst_renderer/        # 104 tests, 4 proof layers
uv run python scripts/benchmark.py           # timing table
uv run python scripts/build_gallery.py       # 105-image contact sheet
uv run uvicorn pocs.poc1_dst_renderer.web.server:app --reload --port 8000
```

See `VERIFICATION.md` for what each test layer proves and known limitations.
