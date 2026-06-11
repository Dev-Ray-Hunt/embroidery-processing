"""Benchmark every POC 1 renderer against every sample DST.

Server renderers (A, B, C): cold + warm wall time in-process, plus output
size. Browser renderers (D, E): panel timing read from the live UI under
headless Chromium — NOTE this is SwiftShader software WebGL; real-GPU numbers
will be better, especially for E.

Writes a markdown table to outputs/benchmark_results.md and prints it.

    uv run python scripts/benchmark.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pocs.poc1_dst_renderer.src import dst_parser  # noqa: E402
from scripts.build_gallery import render_server  # noqa: E402
from shared.design_colors import fabric_rgb  # noqa: E402

DST_DIR = REPO_ROOT / "data" / "sample_dsts"
OUT_PATH = REPO_ROOT / "outputs" / "benchmark_results.md"
PORT = 8923


def bench_server(dsts: list[Path]) -> list[dict]:
    fabric = fabric_rgb("white")
    rows = []
    for dst in dsts:
        meta = dst_parser.parse(dst).metadata
        for rid in ("a", "b", "c"):
            png, cold = render_server(rid, dst, fabric)
            _, warm = render_server(rid, dst, fabric)
            rows.append(
                {
                    "design": dst.name,
                    "stitches": meta["stitch_count"],
                    "renderer": rid.upper(),
                    "cold_ms": cold * 1000,
                    "warm_ms": warm * 1000,
                    "size_kb": len(png) // 1024,
                }
            )
    return rows


def bench_browser(dsts: list[Path]) -> list[dict]:
    from playwright.sync_api import sync_playwright

    rows = []
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
            page = browser.new_page(viewport={"width": 1600, "height": 1200})
            page.goto(base)
            page.wait_for_selector(".dst-item")
            for dst in dsts:
                meta = dst_parser.parse(dst).metadata
                page.locator(".dst-item", has_text=dst.name).click()
                for rid in ("d", "e"):
                    page.wait_for_selector(
                        f'.renderer[data-renderer="{rid}"] .render-area[data-rendered="1"]',
                        timeout=60000,
                    )
                page.wait_for_timeout(300)
                for rid in ("d", "e"):
                    text = page.locator(
                        f'.renderer[data-renderer="{rid}"] .render-area .timing'
                    ).inner_text()
                    m = re.match(r"([\d.]+) ms \(draw ([\d.]+) ms\)", text)
                    total, draw = (float(m.group(1)), float(m.group(2))) if m else (-1, -1)
                    rows.append(
                        {
                            "design": dst.name,
                            "stitches": meta["stitch_count"],
                            "renderer": rid.upper(),
                            "cold_ms": total,
                            "warm_ms": draw,  # for D/E: warm == pure draw time
                            "size_kb": 0,
                        }
                    )
            browser.close()
    finally:
        srv.terminate()
        srv.wait(timeout=10)
    return rows


def main() -> int:
    dsts = sorted(p for p in DST_DIR.iterdir() if p.suffix.lower() == ".dst")
    if not dsts:
        print("No DSTs in data/sample_dsts/.", file=sys.stderr)
        return 1

    print("Benchmarking server renderers...")
    rows = bench_server(dsts)
    print("Benchmarking browser renderers (SwiftShader — software WebGL)...")
    rows += bench_browser(dsts)

    rows.sort(key=lambda r: (r["stitches"], r["renderer"]))
    lines = [
        "# POC 1 renderer benchmarks",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} on this machine. "
        "D/E numbers are headless **SwiftShader (software WebGL)** — treat as "
        "upper bounds; real-GPU is faster. For D/E, cold = fetch+build+draw, "
        "warm = pure draw.",
        "",
        "| Design | Stitches | Renderer | Cold (ms) | Warm (ms) | PNG (KB) |",
        "|--------|---------:|----------|----------:|----------:|---------:|",
    ]
    for r in rows:
        size = str(r["size_kb"]) if r["size_kb"] else "—"
        lines.append(
            f"| {r['design']} | {r['stitches']:,} | {r['renderer']} "
            f"| {r['cold_ms']:.0f} | {r['warm_ms']:.0f} | {size} |"
        )
    out = "\n".join(lines)
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(out)
    print(out)
    print(f"\nWritten to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
