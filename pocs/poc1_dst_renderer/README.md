# POC 1: DST Renderer Bake-Off

Spec: [../../POC_1_DST_Renderer.md](../../POC_1_DST_Renderer.md)

Render existing DST files as realistic visual previews suitable for customer proof approval. Compare 5 rendering approaches (pyembroidery PNG, Pillow 2D, Cairo 2D, HTML5 Canvas, WebGL/Three.js) and recommend a primary + secondary renderer.

**Status:** scaffolded; no code yet. Start with [NEXT.md](NEXT.md).

**Layout:**

```
poc1_dst_renderer/
├── README.md       (this file)
├── NEXT.md         (explicit first task — DST parsing foundation)
├── FINDINGS.md     (writeup deliverable — fill in as bake-off proceeds)
├── src/            (Python parser + Python-side renderers)
└── tests/          (pytest tests against parsed-stitch JSON)
```

JS-based renderers (options D and E) will get their own directory under this POC when they start — likely `web/` or `frontend/`. Defer until then.

**Test inputs:** public sample DSTs only, dropped into `data/sample_dsts/` (gitignored). See `data/README.md` at repo root.

**Outputs:** rendered images, scorecards, comparison galleries → `outputs/poc1/` (gitignored).
