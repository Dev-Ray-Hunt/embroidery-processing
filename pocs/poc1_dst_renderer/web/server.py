"""POC 1 Bake-off dev UI — FastAPI server.

Run from the repo root:

    uv run uvicorn pocs.poc1_dst_renderer.web.server:app --reload --port 8000

Then open http://localhost:8000 in a browser.

This is dev tooling for visual comparison during the renderer bake-off.
The production app's web stack will be picked in POC 4 — nothing about
this server's framework choice is meant to bind that decision.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from pocs.poc1_dst_renderer.src import dst_parser
from pocs.poc1_dst_renderer.src.renderers import a_pyembroidery, b_pillow
from shared.design_colors import DEFAULT_FABRIC, FABRICS, fabric_rgb


def _render_a_on_fabric(dst_path: Path, *, fabric: tuple[int, int, int]) -> bytes:
    """Renderer A composited over a fabric color.

    pyembroidery's PngWriter has no background option (transparent only), so
    the harness composites — A itself gets no credit for fabric support in the
    bake-off, but its panel stays comparable to the others.
    """
    import io

    from PIL import Image

    raw = a_pyembroidery.render_png(dst_path)
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    bg = Image.new("RGBA", img.size, (*fabric, 255))
    out = Image.alpha_composite(bg, img).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


# Resolve the repo root from this file's location:
# pocs/poc1_dst_renderer/web/server.py -> ../../../
REPO_ROOT = Path(__file__).resolve().parents[3]
DST_DIR = REPO_ROOT / "data" / "sample_dsts"
STATIC_DIR = Path(__file__).parent / "static"


# Renderer registry — a renderer entry maps a short id to a panel-shaped record.
# `kind` is "server" if the backend produces the PNG, "client" if the browser does.
# `impl` is the callable for server-side renderers; None for client-side.
RENDERERS: dict[str, dict] = {
    "a": {
        "title": "A. pyembroidery PNG",
        "desc": "Baseline — pyembroidery's built-in PNG writer. Zero custom code.",
        "kind": "server",
        "impl": _render_a_on_fabric,
        "implemented": True,
    },
    "b": {
        "title": "B. Pillow 2D + shading",
        "desc": "Custom Python renderer: thick lines with angle-based brightness shading.",
        "kind": "server",
        "impl": b_pillow.render_png,
        "implemented": True,
    },
    "c": {
        "title": "C. Cairo 2D antialiased",
        "desc": "PyCairo vector renderer with smooth antialiased lines.",
        "kind": "server",
        "impl": None,
        "implemented": False,
    },
    "d": {
        "title": "D. HTML5 Canvas (browser)",
        "desc": "Browser-side canvas with rounded line caps. Interactive zoom/pan.",
        "kind": "client",
        "impl": None,
        "implemented": False,
    },
    "e": {
        "title": "E. WebGL/Three.js 2.5D",
        "desc": "Three.js scene with shaded thread geometry.",
        "kind": "client",
        "impl": None,
        "implemented": False,
    },
}


app = FastAPI(title="POC 1 — DST Renderer Bake-off")


@app.get("/api/renderers")
def list_renderers() -> list[dict]:
    """Return panel metadata for the frontend grid."""
    return [
        {
            "id": rid,
            "title": r["title"],
            "desc": r["desc"],
            "kind": r["kind"],
            "implemented": r["implemented"],
        }
        for rid, r in RENDERERS.items()
    ]


@app.get("/api/fabrics")
def list_fabrics() -> list[dict]:
    """The three POC fabric backgrounds, for the UI selector."""
    return [
        {"name": name, "hex": "#{:02x}{:02x}{:02x}".format(*rgb), "default": name == DEFAULT_FABRIC}
        for name, rgb in FABRICS.items()
    ]


@app.get("/api/dsts")
def list_dsts() -> list[dict]:
    """List DST files in data/sample_dsts/ with parser-derived metadata."""
    if not DST_DIR.exists():
        return []

    # Case-insensitive: real DST files (and the Embroidermodder samples) are
    # often named .DST. pathlib.glob is case-sensitive on macOS, so match by suffix.
    dsts = sorted(p for p in DST_DIR.iterdir() if p.suffix.lower() == ".dst")
    out: list[dict] = []
    for p in dsts:
        entry: dict = {
            "name": p.name,
            "size_bytes": p.stat().st_size,
        }
        try:
            design = dst_parser.parse(p)
            m = design.metadata
            entry.update(
                {
                    "stitches": m["stitch_count"],
                    "commands": m["command_count"],
                    "color_blocks": m["color_block_count"],
                    "extents": list(design.extents),
                    "width_mm": m["width_mm"],
                    "height_mm": m["height_mm"],
                }
            )
        except Exception as e:  # noqa: BLE001 — surface any parser failure to the UI
            entry["error"] = f"{type(e).__name__}: {e}"
        out.append(entry)
    return out


@app.get("/api/render/{renderer_id}/{filename}")
def render(renderer_id: str, filename: str, fabric: str = DEFAULT_FABRIC) -> Response:
    """Run the named server-side renderer and return PNG bytes."""
    renderer = RENDERERS.get(renderer_id)
    if renderer is None:
        raise HTTPException(status_code=404, detail=f"Unknown renderer: {renderer_id}")
    if not renderer["implemented"]:
        raise HTTPException(status_code=501, detail=f"Renderer {renderer_id} not implemented yet")
    if renderer["kind"] != "server":
        raise HTTPException(
            status_code=400,
            detail=f"Renderer {renderer_id} is client-side; render in browser.",
        )
    if fabric not in FABRICS:
        raise HTTPException(
            status_code=400, detail=f"Unknown fabric: {fabric} (expected one of {list(FABRICS)})"
        )

    # Lock the file path inside DST_DIR — no traversal, no symlink escapes.
    safe_name = Path(filename).name
    dst_path = (DST_DIR / safe_name).resolve()
    if not dst_path.is_file() or DST_DIR.resolve() not in dst_path.parents:
        raise HTTPException(status_code=404, detail=f"DST not found: {filename}")

    try:
        png_bytes = renderer["impl"](dst_path, fabric=fabric_rgb(fabric))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Render failed: {e}") from e

    return Response(content=png_bytes, media_type="image/png")


# Static frontend served at /
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
