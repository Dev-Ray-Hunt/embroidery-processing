# POC 1 — Bake-off Dev UI

A locally-hosted web UI for visually comparing the 5 DST renderers side-by-side. Pick a DST from the sidebar, see all the renderer panels update.

This is **dev tooling**, not the production app. It's the comparison harness for the renderer bake-off. The production app's web stack is its own decision (see [POC 4 spec](../../../POC_4_Order_Workflow.md) for that bake-off).

## Run it

From the repo root:

```bash
uv run uvicorn pocs.poc1_dst_renderer.web.server:app --reload --port 8000
```

Open <http://localhost:8000>.

The `--reload` flag picks up Python changes without restarting. Static files (HTML/CSS/JS) reload on browser refresh.

API docs (handy for poking at endpoints): <http://localhost:8000/docs>

## What it does today

- **Sidebar:** lists every `*.dst` in `data/sample_dsts/` with stitch count, color-block count, and physical size in mm. Files that fail to parse show an error in red.
- **Main grid:** one panel per bake-off renderer (A through E). Click a DST in the sidebar and every implemented panel re-renders.

| Panel | Status | Notes |
|---|---|---|
| A. pyembroidery PNG | ✅ working | Server-side. Calls `pyembroidery.write_png`. Zero custom rendering code. |
| B. Pillow 2D + shading | placeholder | Will land as `src/renderers/b_pillow.py`. |
| C. Cairo 2D antialiased | placeholder | Needs `pycairo` dep when implemented. |
| D. HTML5 Canvas (browser) | placeholder | Browser-side. Needs a `/api/parse/{filename}` endpoint to ship stitch data to the client. |
| E. WebGL/Three.js | placeholder | Browser-side. Same data path as D. |

## Architecture

```
web/
├── server.py              FastAPI app — /api/dsts, /api/renderers, /api/render/{r}/{f}
├── static/
│   ├── index.html         Main page — sidebar + grid skeleton
│   ├── app.js             Vanilla JS — fetches APIs, re-renders panels on selection
│   └── style.css          Layout + panel styling
└── README.md              This file
```

Renderer implementations live in `../src/renderers/`. The server imports each implemented module and registers it in the `RENDERERS` dict. Adding a new renderer is one new file in `src/renderers/` plus one new entry in the registry.

## How the panels update

Selecting a DST triggers `selectDst(filename)` in `app.js`, which kicks off `Promise.all` over every implemented server-side renderer. Each panel does a `fetch('/api/render/<id>/<filename>')`, gets back PNG bytes, blob-URLs them into an `<img>`, and overlays a wall-clock render time in the corner.

Client-side renderers (D, E) will hook into the same `selectDst` flow but call into a different `renderInBrowser(rendererId, filename)` path that pulls stitch JSON from the backend and draws on a `<canvas>` element inside the panel.

## Adding a new server-side renderer

1. Create `pocs/poc1_dst_renderer/src/renderers/<id>_<name>.py` exporting `render_png(dst_path: Path) -> bytes`.
2. Import it in `server.py` and flip the renderer's `impl` and `implemented` fields.
3. Done — the frontend picks it up automatically from `/api/renderers`.
