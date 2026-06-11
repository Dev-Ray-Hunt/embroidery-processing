# POC 1 Renderer Verification

How renderers B–E were proven to work without a human watching, what each
check actually demonstrates, and what it deliberately does not claim.
Built 2026-06-10 on the `claude/poc1-renderers-b-e` branch.

## TL;DR

**104 automated tests, all passing** at the final commit, across four proof
layers. Two real bugs were caught by the harness during development (color-
change connectors, renderer E's missing clear color) — evidence the checks
bite. The one thing no test here claims: that the renders are *beautiful*.
That's the human pass — gallery + live UI + (eventually) the stitched photo.

Re-run everything:

```bash
uv run pytest pocs/poc1_dst_renderer/ -v
```

Suite runtime ≈ 35 s (includes booting a real server + headless Chromium).

## The four proof layers

### Layer 1 — Synthetic fixtures (`test_renderers_synthetic.py`, 13 tests)

Hand-built designs where correct output is *knowable*, run against B and C
directly. No sample data needed — these are the durable CI tests.

| Check | Proves |
|---|---|
| Hollow square: frame inked, centre + margins fabric | Coordinates land where they should; no fill where there's no thread |
| Two-block design: both palette colors present, in the right vertical order | COLOR_CHANGE advances the palette; blocks land in correct positions |
| Jump design: gap between bars stays fabric | JUMP moves the pen without drawing |
| All 3 fabrics fill the background exactly | Fabric parameter is honored end-to-end |
| Horizontal stitches ≥15% brighter than vertical (B) | The angle-shading feature actually does something measurable |

### Layer 2 — Cross-renderer consistency (`test_renderers_real_dsts.py`)

A, B and C render every sample DST; their ink masks (binary thread-vs-fabric,
cropped to ink bbox, normalized to a 96×96 grid) must agree pairwise with
**IoU ≥ 0.55**. The floor is evidence-based: correct renders measured
0.64–0.99 across the corpus; a deliberately Y-flipped render measures
0.10–0.41. A coordinate, scale, or axis bug in any one renderer cannot pass.

In the browser layer, D and E masks are likewise compared against B's
server-side render (floors 0.55 / 0.45 — E sits lower because 3D lighting
thickens its silhouette).

### Layer 3 — Property checks (`test_renderers_real_dsts.py`, with layer 2: 50 tests)

Per real DST × renderer: ink bbox aspect ratio matches the design extents
(±12%), every color block's palette color appears in the output, fabric
reaches all four corners, and the largest design renders inside the POC's
10-second bar.

### Layer 4 — Browser verification (`test_browser_renderers.py`, 13 tests)

Playwright + headless Chromium drives the *actual* bake-off UI against a
*actual* uvicorn server — no mocks:

- Page boots with **zero JS errors** (console and pageerror both captured,
  asserted empty again at session end).
- D and E panels paint real ink on fabric (≥5% ink coverage; corners fabric).
- D/E geometry agrees with server renderer B (mask IoU, see layer 2).
- **Interactivity does something:** wheel zoom, drag pan repaint both panels;
  D's hover dims the non-hovered blocks; E's shift-drag tilt repaints.
- Fabric switch restyles both client panels in place (corner pixel becomes
  navy, then restored to white).

## Bugs the harness caught (both fixed in this branch)

1. **Color-change connectors.** B, C, D and E all initially drew a segment
   from the last stitch of one color block into the first stitch of the next
   — in the new block's color. Real thread is cut at a color change. Caught
   by the layer-1 two-block fixture (the "top bar" assertion found red where
   blue belonged).
2. **Renderer E's black void.** No WebGL clear color was set, so panels whose
   aspect ratio outgrew the fabric plane showed black bars — which also
   poisoned E's ink masks. Caught by layer 4's corner-fabric assertion.

## Known limitations — read before trusting

- **No beauty claim.** Every check is geometric/chromatic. Whether a render
  looks like embroidery to a customer is Brandon's call (gallery + photo).
- **SwiftShader, not your GPU.** Headless Chromium renders WebGL in software.
  E's correctness is proven; its *performance* numbers are upper bounds, and
  its lighting may differ subtly from a real GPU. Eyeball it live.
- **Renderer A is composited.** A has no background support; the harness lays
  its transparent PNG over the fabric color. A's panel is comparable, but A
  itself earns no fabric credit.
- **Interactivity is verified as "events repaint correctly,"** not as "feels
  good." Feel is a human judgment.
- **The corpus tops out at 63,710 stitches.** Scalability beyond that is
  extrapolation.
- Layer 2+3 tests **skip silently when `data/sample_dsts/` is empty** (the
  files are gitignored). A fresh clone runs only layers 1 and the API tests
  until DSTs are restored — check the skip count in pytest output.

## Verification results at final commit

```
104 passed (0 failed, 0 skipped) in ~35 s
  test_dst_parser.py ............... 28  (parser internal consistency, 4 checks x 7 DSTs)
  test_renderers_synthetic.py ...... 13  (layer 1)
  test_renderers_real_dsts.py ...... 50  (layers 2+3)
  test_browser_renderers.py ........ 13  (layer 4)
```

Plus, outside pytest: `scripts/build_gallery.py` produced all 105
renderer×design×fabric images without error, and `scripts/benchmark.py`
completed the full timing matrix (results embedded in FINDINGS.md).
