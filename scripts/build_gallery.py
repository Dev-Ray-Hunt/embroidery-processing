"""Build the POC 1 comparison gallery: every renderer x DST x fabric.

Server renderers (A, B, C) render in-process; browser renderers (D, E) are
screenshotted from the live bake-off UI via headless Chromium (their panel
timing badges are left visible — they're part of the evidence).

Output: outputs/gallery/<design>/<renderer>_<fabric>.png plus a contact-sheet
outputs/gallery/index.html (rows = renderer, columns = fabric, one section
per design). outputs/ is gitignored — renders of team-supplied DSTs must
never land in git. Re-run any time:

    uv run python scripts/build_gallery.py
"""

from __future__ import annotations

import html
import io
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pocs.poc1_dst_renderer.src.renderers import (  # noqa: E402
    a_pyembroidery,
    b_pillow,
    c_cairo,
)
from shared.design_colors import FABRICS  # noqa: E402

DST_DIR = REPO_ROOT / "data" / "sample_dsts"
OUT_DIR = REPO_ROOT / "outputs" / "gallery"
PORT = 8919

RENDERER_TITLES = {
    "a": "A. pyembroidery PNG (baseline)",
    "b": "B. Pillow 2D + angle shading",
    "c": "C. Cairo antialiased vector",
    "d": "D. HTML5 Canvas (browser)",
    "e": "E. Three.js 2.5D (browser)",
}


def render_server(rid: str, dst_path: Path, fabric: tuple[int, int, int]) -> tuple[bytes, float]:
    t0 = time.perf_counter()
    if rid == "a":
        raw = a_pyembroidery.render_png(dst_path)
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        bg = Image.new("RGBA", img.size, (*fabric, 255))
        out = io.BytesIO()
        Image.alpha_composite(bg, img).convert("RGB").save(out, format="PNG")
        png = out.getvalue()
    elif rid == "b":
        png = b_pillow.render_png(dst_path, fabric=fabric)
    else:
        png = c_cairo.render_png(dst_path, fabric=fabric)
    return png, time.perf_counter() - t0


def shoot_browser_panels(dsts: list[Path]) -> dict[tuple[str, str, str], tuple[bytes, float]]:
    """Screenshot D/E panels for every design x fabric from the live UI.

    Returns {(design, renderer, fabric): (png_bytes, wall_seconds)}.
    """
    from playwright.sync_api import sync_playwright

    shots: dict[tuple[str, str, str], tuple[bytes, float]] = {}
    srv = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "pocs.poc1_dst_renderer.web.server:app",
            "--port",
            str(PORT),
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        base = f"http://127.0.0.1:{PORT}"
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{base}/api/renderers", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--enable-unsafe-swiftshader"])
            page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
            page.goto(base)
            page.wait_for_selector(".dst-item")
            for dst in dsts:
                for fabric_name in FABRICS:
                    t0 = time.perf_counter()
                    page.locator(f'.fabric-swatch[data-fabric="{fabric_name}"]').click()
                    page.locator(".dst-item", has_text=dst.name).click()
                    for rid in ("d", "e"):
                        page.wait_for_selector(
                            f'.renderer[data-renderer="{rid}"] .render-area[data-rendered="1"]',
                            timeout=60000,
                        )
                    page.wait_for_timeout(500)
                    elapsed = time.perf_counter() - t0
                    for rid in ("d", "e"):
                        png = page.locator(
                            f'.renderer[data-renderer="{rid}"] .render-area'
                        ).screenshot()
                        shots[(dst.name, rid, fabric_name)] = (png, elapsed)
                    print(f"  browser {dst.name} on {fabric_name}: {elapsed:.1f}s")
            browser.close()
    finally:
        srv.terminate()
        srv.wait(timeout=10)
    return shots


def main() -> int:
    dsts = sorted(p for p in DST_DIR.iterdir() if p.suffix.lower() == ".dst")
    if not dsts:
        print("No DSTs in data/sample_dsts/ — nothing to render.", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    timings: dict[tuple[str, str, str], float] = {}

    print("Rendering server panels (A, B, C)...")
    for dst in dsts:
        design_dir = OUT_DIR / dst.stem
        design_dir.mkdir(exist_ok=True)
        for rid in ("a", "b", "c"):
            for fabric_name, fabric in FABRICS.items():
                png, secs = render_server(rid, dst, fabric)
                (design_dir / f"{rid}_{fabric_name}.png").write_bytes(png)
                timings[(dst.name, rid, fabric_name)] = secs
        print(f"  {dst.name} done")

    print("Screenshotting browser panels (D, E)...")
    shots = shoot_browser_panels(dsts)
    for (design, rid, fabric_name), (png, secs) in shots.items():
        stem = next(d.stem for d in dsts if d.name == design)
        (OUT_DIR / stem / f"{rid}_{fabric_name}.png").write_bytes(png)
        timings[(design, rid, fabric_name)] = secs

    # Contact sheet.
    rows = [
        "<!doctype html><meta charset='utf-8'><title>POC 1 gallery</title>",
        "<style>body{font-family:system-ui;margin:2rem;background:#fafafa}"
        "h2{margin-top:3rem}table{border-collapse:collapse}"
        "td,th{border:1px solid #ddd;padding:6px;text-align:center;vertical-align:top}"
        "img{max-width:300px;display:block}small{color:#666}</style>",
        "<h1>POC 1 — renderer × fabric gallery</h1>",
        f"<p>{len(dsts)} designs × 5 renderers × {len(FABRICS)} fabrics. "
        "Generated by scripts/build_gallery.py — regenerate freely, never commit.</p>",
    ]
    for dst in dsts:
        rows.append(f"<h2>{html.escape(dst.name)}</h2><table><tr><th></th>")
        rows.extend(f"<th>{f}</th>" for f in FABRICS)
        rows.append("</tr>")
        for rid, title in RENDERER_TITLES.items():
            rows.append(f"<tr><th>{html.escape(title)}</th>")
            for fabric_name in FABRICS:
                rel = f"{dst.stem}/{rid}_{fabric_name}.png"
                secs = timings.get((dst.name, rid, fabric_name))
                note = f"<small>{secs * 1000:.0f} ms</small>" if secs is not None else ""
                rows.append(f"<td><img src='{rel}' loading='lazy'>{note}</td>")
            rows.append("</tr>")
        rows.append("</table>")
    (OUT_DIR / "index.html").write_text("\n".join(rows))

    n = len(dsts) * 5 * len(FABRICS)
    print(f"\nGallery: {n} images -> {OUT_DIR / 'index.html'}")
    print("Open with:  open outputs/gallery/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
