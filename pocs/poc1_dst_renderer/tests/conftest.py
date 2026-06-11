"""Shared fixtures and image-analysis helpers for the renderer test suite.

Four proof layers (see VERIFICATION.md):
1. Synthetic fixtures — hand-built designs with knowable correct output.
2. Cross-renderer consistency — ink-mask IoU between renderer pairs.
3. Property checks — aspect/extents/colors per real sample DST.
4. Browser verification — Playwright drives the real UI for renderers D/E.

Sample DSTs are gitignored; tests that need them skip cleanly when absent.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from pocs.poc1_dst_renderer.src.dst_parser import ParsedDesign

REPO_ROOT = Path(__file__).resolve().parents[3]
DST_DIR = REPO_ROOT / "data" / "sample_dsts"
DST_FILES = (
    sorted(p for p in DST_DIR.iterdir() if p.suffix.lower() == ".dst") if DST_DIR.exists() else []
)


# --- Synthetic design construction ----------------------------------------


def make_design(
    stitches: list[tuple[float, float, str]], source: str = "synthetic"
) -> ParsedDesign:
    """Build a ParsedDesign from a raw stitch list, deriving the metadata the
    same way the parser does."""
    xs = [s[0] for s in stitches]
    ys = [s[1] for s in stitches]
    color_changes = [i for i, s in enumerate(stitches) if s[2] == "COLOR_CHANGE"]
    counts = {
        name: sum(1 for s in stitches if s[2] == name)
        for name in ("STITCH", "JUMP", "TRIM", "COLOR_CHANGE")
    }
    extents = (min(xs), min(ys), max(xs), max(ys))
    return ParsedDesign(
        source=source,
        stitches=stitches,
        color_change_indices=color_changes,
        extents=extents,
        metadata={
            "stitch_count": counts["STITCH"],
            "command_count": len(stitches),
            "jump_count": counts["JUMP"],
            "trim_count": counts["TRIM"],
            "color_change_count": counts["COLOR_CHANGE"],
            "color_block_count": counts["COLOR_CHANGE"] + 1,
            "width_mm": round((extents[2] - extents[0]) / 10, 1),
            "height_mm": round((extents[3] - extents[1]) / 10, 1),
        },
    )


def dense_line(x0: float, y0: float, x1: float, y1: float, n: int = 20) -> list:
    """A run of short STITCH commands along a line — like a real satin column."""
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, "STITCH"))
    return pts


# --- Image analysis ---------------------------------------------------------


def to_image(png_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png_bytes)).convert("RGB")


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return (sum((x - y) ** 2 for x, y in zip(a, b, strict=False))) ** 0.5


def ink_mask(img: Image.Image, fabric: tuple[int, int, int], threshold: int = 48) -> Image.Image:
    """Binary mask of pixels that differ meaningfully from the fabric color."""
    px = img.load()
    mask = Image.new("L", img.size, 0)
    mpx = mask.load()
    for y in range(img.height):
        for x in range(img.width):
            if color_distance(px[x, y], fabric) > threshold:
                mpx[x, y] = 255
    return mask


def ink_bbox(mask: Image.Image) -> tuple[int, int, int, int] | None:
    return mask.getbbox()


def normalized_mask(mask: Image.Image, grid: int = 96) -> Image.Image:
    """Crop a mask to its ink bbox and resize to a common grid, removing
    margin/scale differences between renderers before comparing shapes."""
    bbox = mask.getbbox()
    if bbox is None:
        return Image.new("L", (grid, grid), 0)
    return mask.crop(bbox).resize((grid, grid), Image.NEAREST)


def mask_iou(a: Image.Image, b: Image.Image) -> float:
    """Intersection-over-union of two equal-size binary masks."""
    pa, pb = a.load(), b.load()
    inter = union = 0
    for y in range(a.height):
        for x in range(a.width):
            ia, ib = pa[x, y] > 0, pb[x, y] > 0
            inter += ia and ib
            union += ia or ib
    return inter / union if union else 0.0


def ink_fraction(mask: Image.Image) -> float:
    hist = mask.histogram()
    return hist[255] / (mask.width * mask.height)


def has_color_near(img: Image.Image, target: tuple[int, int, int], tol: float = 60) -> bool:
    """True if any pixel is within `tol` euclidean distance of `target`.

    Samples on a coarse stride for speed; callers use it on 1000px renders
    where every color block covers far more than a 3px stride.
    """
    px = img.load()
    for y in range(0, img.height, 3):
        for x in range(0, img.width, 3):
            if color_distance(px[x, y], target) <= tol:
                return True
    return False


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture(scope="session")
def sample_dsts() -> list[Path]:
    if not DST_FILES:
        pytest.skip("no sample DSTs in data/sample_dsts/ (gitignored)")
    return DST_FILES


@pytest.fixture(scope="session")
def live_server():
    """A real uvicorn serving the bake-off app, for browser tests."""
    import subprocess
    import sys
    import time
    import urllib.request

    port = 8911
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "pocs.poc1_dst_renderer.web.server:app",
            "--port",
            str(port),
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{base}/api/renderers", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            pytest.fail("bake-off server did not become ready")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="session")
def pw():
    """The ONE sync Playwright instance for the whole test session.

    Two test modules each starting their own sync_playwright() collide (the
    sync API allows a single instance per thread), so every browser fixture
    must launch from this shared instance.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")
    p = sync_playwright().start()
    yield p
    p.stop()


@pytest.fixture(scope="session")
def browser_page(pw, live_server):
    """A Chromium page on the live server, software-WebGL enabled.

    Skips (not fails) if Playwright's chromium isn't installed, so the rest
    of the suite stays runnable on machines without browsers.
    """
    try:
        browser = pw.chromium.launch(args=["--enable-unsafe-swiftshader"])
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"chromium unavailable: {e}")
    page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on(
        "console",
        lambda m: errors.append(f"console.error: {m.text}") if m.type == "error" else None,
    )
    page.js_errors = errors  # type: ignore[attr-defined]
    yield page
    browser.close()
