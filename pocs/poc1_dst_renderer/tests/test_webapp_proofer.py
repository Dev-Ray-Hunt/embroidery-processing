"""Verification for the portable Stitch Proofer (webapp/DST_Render_Test.html).

Two claims to prove:

1. PARSER PARITY — the in-browser JS DST parser decodes exactly what our
   Python parser (pyembroidery-backed) decodes: same stitch count, same
   absolute stitch coordinates, same per-block stitch counts, same extents.
   (Command streams differ legitimately: pyembroidery post-processes jump
   runs into TRIMs; the proofer doesn't need to. Stitches are the truth.)

2. THE UI WORKS — loaded straight from file:// (no server: that's the
   portability claim), a real browser can open a DST via the file input,
   see ink, recolor a block, highlight a block, zoom to true 1:1, and pan.

Skips cleanly without sample DSTs or Chromium.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from pocs.poc1_dst_renderer.src import dst_parser
from pocs.poc1_dst_renderer.tests.conftest import (
    DST_FILES,
    REPO_ROOT,
    color_distance,
    ink_fraction,
    ink_mask,
)

pytestmark = pytest.mark.skipif(
    not DST_FILES, reason="no sample DSTs in data/sample_dsts/ (gitignored)"
)

PROOFER_URL = (REPO_ROOT / "webapp" / "DST_Render_Test.html").as_uri()
WHITE = (242, 241, 236)
_ids = [p.name for p in DST_FILES]


@pytest.fixture(scope="module")
def proofer_page():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")
    with sync_playwright() as p:
        try:
            # SwiftShader: the 2.5D mode needs WebGL2 in headless Chromium.
            browser = p.chromium.launch(args=["--enable-unsafe-swiftshader"])
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"chromium unavailable: {e}")
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.js_errors = errors  # type: ignore[attr-defined]
        page.goto(PROOFER_URL)
        yield page
        browser.close()


def _load(page, dst_path) -> None:
    page.locator("#file-input").set_input_files(str(dst_path))
    page.wait_for_function("() => window.__proofer.state.design !== null")
    page.wait_for_timeout(150)


def _canvas_shot(page) -> Image.Image:
    # Shoot the viewport, not a specific canvas: the 2.5D mode swaps in a
    # separate WebGL canvas, and the viewport always shows whichever is live.
    return Image.open(io.BytesIO(page.locator("#viewport").screenshot())).convert("RGB")


def _set_mode(page, mode: str) -> None:
    page.locator(f'#renderer-row button[data-mode="{mode}"]').click()
    page.wait_for_timeout(200)


# --------------------------- 1. Parser parity --------------------------------


@pytest.mark.parametrize("dst_path", DST_FILES, ids=_ids)
def test_js_parser_matches_python_parser(proofer_page, dst_path):
    _load(proofer_page, dst_path)
    js = proofer_page.evaluate(
        """() => {
          const d = window.__proofer.state.design;
          // Stitch POINTS per color block. (Drawn-segment counts are not
          // parity-comparable: pyembroidery's trim interpolation rewrites
          // jump records around block starts, which shifts where the pen
          // 'was' before a block's first stitch by one move.)
          const perBlock = [0];
          for (const [, , cmd] of d.stitches) {
            if (cmd === 'STITCH') perBlock[perBlock.length - 1]++;
            else if (cmd === 'COLOR_CHANGE') perBlock.push(0);
          }
          return {
            stitchCount: d.counts.stitches,
            colorChanges: d.counts.colorChanges,
            extents: d.extents,
            blockStitchPoints: perBlock,
            stitchCoords: d.stitches.filter((s) => s[2] === 'STITCH').map((s) => [s[0], s[1]]),
          };
        }"""
    )

    py = dst_parser.parse(dst_path)
    py_coords = [[x, y] for x, y, cmd in py.stitches if cmd == "STITCH"]

    assert js["stitchCount"] == py.metadata["stitch_count"]
    assert js["colorChanges"] == py.metadata["color_change_count"]
    assert js["stitchCoords"] == py_coords, "stitch coordinate streams differ"

    py_blocks = [0]
    for _, _, cmd in py.stitches:
        if cmd == "STITCH":
            py_blocks[-1] += 1
        elif cmd == "COLOR_CHANGE":
            py_blocks.append(0)
    assert js["blockStitchPoints"] == py_blocks

    # Extents over stitch points only.
    xs = [c[0] for c in py_coords]
    ys = [c[1] for c in py_coords]
    assert js["extents"] == [min(xs), min(ys), max(xs), max(ys)]


# --------------------------- 2. UI behavior ----------------------------------


def test_loads_from_file_url_with_no_js_errors(proofer_page):
    assert proofer_page.url.startswith("file://")
    _load(proofer_page, DST_FILES[0])
    assert proofer_page.js_errors == [], f"JS errors: {proofer_page.js_errors}"


def test_renders_ink_and_design_info(proofer_page):
    dst = DST_FILES[0]
    _load(proofer_page, dst)
    info = proofer_page.locator("#design-info").inner_text()
    meta = dst_parser.parse(dst).metadata
    assert f"{meta['stitch_count']:,}" in info
    assert "mm" in info
    img = _canvas_shot(proofer_page)
    assert ink_fraction(ink_mask(img, WHITE)) > 0.01, "canvas has (nearly) no ink"


def test_block_color_picker_recolors_design(proofer_page):
    _load(proofer_page, DST_FILES[0])
    before = _canvas_shot(proofer_page)
    proofer_page.locator(".block-row input[type=color]").first.fill("#00ff37")
    proofer_page.wait_for_timeout(150)
    after = _canvas_shot(proofer_page)
    assert list(before.getdata()) != list(after.getdata()), "recolor did not repaint"
    # The chosen color must actually appear in the render.
    px = after.load()
    found = any(
        color_distance(px[x, y], (0, 255, 55)) < 60
        for y in range(0, after.height, 4)
        for x in range(0, after.width, 4)
    )
    assert found, "picked color never appears on the canvas"


def test_block_highlight_dims_other_blocks(proofer_page):
    multi = next((p for p in DST_FILES if p.name == "000021273.DST"), None)
    if multi is None:
        pytest.skip("multi-block test design not in corpus")
    _load(proofer_page, multi)
    before = _canvas_shot(proofer_page)
    proofer_page.locator(".block-row").first.click()
    proofer_page.wait_for_timeout(150)
    after = _canvas_shot(proofer_page)
    assert list(before.getdata()) != list(after.getdata()), "highlight did not repaint"
    proofer_page.locator(".block-row").first.click()  # toggle off again


def test_one_to_one_zoom_is_physically_correct(proofer_page):
    """1:1 means one DST unit (0.1 mm) spans exactly 0.1 mm of CSS space
    (96 px/inch reference): scale must equal 96/25.4 * 0.1 px/unit."""
    _load(proofer_page, DST_FILES[0])
    proofer_page.locator("#zoom-100").click()
    scale = proofer_page.evaluate("() => window.__proofer.state.scale")
    assert scale == pytest.approx(96 / 25.4 * 0.1, rel=1e-6)
    label = proofer_page.locator("#zoom-label").inner_text()
    assert label == "100%"


def test_wheel_zoom_and_pan_repaint(proofer_page):
    _load(proofer_page, DST_FILES[0])
    box = proofer_page.locator("#stage").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    before = _canvas_shot(proofer_page)
    proofer_page.mouse.move(cx, cy)
    proofer_page.mouse.wheel(0, -480)
    proofer_page.wait_for_timeout(150)
    zoomed = _canvas_shot(proofer_page)
    assert list(before.getdata()) != list(zoomed.getdata()), "wheel zoom did not repaint"
    proofer_page.mouse.down()
    proofer_page.mouse.move(cx + 80, cy + 40, steps=4)
    proofer_page.mouse.up()
    proofer_page.wait_for_timeout(150)
    panned = _canvas_shot(proofer_page)
    assert list(zoomed.getdata()) != list(panned.getdata()), "drag pan did not repaint"


def test_fabric_switch_changes_background(proofer_page):
    _load(proofer_page, DST_FILES[0])
    proofer_page.locator('#fabric-row button[data-fabric="navy"]').click()
    proofer_page.locator("#zoom-fit").click()
    proofer_page.wait_for_timeout(150)
    img = _canvas_shot(proofer_page)
    corner = img.load()[6, 6]
    assert color_distance(corner, (35, 47, 75)) < 30, f"corner {corner} is not navy"
    proofer_page.locator('#fabric-row button[data-fabric="white"]').click()


def test_all_four_renderer_modes_paint_ink(proofer_page):
    """Every bake-off style must produce a real render, and the styles must
    agree on geometry: each mode's ink mask vs flat-mode IoU over a floor."""
    from pocs.poc1_dst_renderer.tests.conftest import mask_iou, normalized_mask

    multi = next((p for p in DST_FILES if p.name == "000021273.DST"), DST_FILES[0])
    _load(proofer_page, multi)
    masks = {}
    for mode in ("flat", "shaded", "soft", "lit"):
        _set_mode(proofer_page, mode)
        img = _canvas_shot(proofer_page)
        mask = ink_mask(img.resize((300, 300)), WHITE)
        assert ink_fraction(mask) > 0.01, f"mode {mode} painted (nearly) nothing"
        masks[mode] = normalized_mask(mask)
    for mode in ("shaded", "soft", "lit"):
        iou = mask_iou(masks["flat"], masks[mode])
        floor = 0.40 if mode == "lit" else 0.60
        assert iou >= floor, f"mode {mode} geometry disagrees with flat (IoU {iou:.3f} < {floor})"
    _set_mode(proofer_page, "shaded")


def test_lit_mode_recolor_and_tilt(proofer_page):
    """The WebGL path has its own color buffers and camera: recoloring a
    block and shift-drag tilting must both repaint correctly."""
    _load(proofer_page, DST_FILES[0])
    _set_mode(proofer_page, "lit")
    proofer_page.locator(".block-row input[type=color]").first.fill("#ff00d0")
    proofer_page.wait_for_timeout(200)
    img = _canvas_shot(proofer_page)
    px = img.load()
    found = any(
        color_distance(px[x, y], (255, 0, 208)) < 90
        for y in range(0, img.height, 4)
        for x in range(0, img.width, 4)
    )
    assert found, "picked color never appears in the 2.5D render"

    before = _canvas_shot(proofer_page)
    box = proofer_page.locator("#viewport").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    proofer_page.keyboard.down("Shift")
    proofer_page.mouse.move(cx, cy)
    proofer_page.mouse.down()
    proofer_page.mouse.move(cx, cy + 70, steps=4)
    proofer_page.mouse.up()
    proofer_page.keyboard.up("Shift")
    proofer_page.wait_for_timeout(200)
    after = _canvas_shot(proofer_page)
    assert list(before.getdata()) != list(after.getdata()), "tilt did not repaint"
    tilt = proofer_page.evaluate("() => window.__proofer.state.tilt")
    assert tilt > 0, "tilt state did not change"
    _set_mode(proofer_page, "shaded")


def test_loading_new_design_in_every_mode_keeps_rendering(proofer_page):
    """Regression: loading a design while the 2.5D mode was active fit the
    view against the hidden (0x0) 2D canvas, collapsing scale to 0 — blank
    screen that persisted across mode switches. Every mode must survive a
    fresh load with a sane scale and visible ink."""
    others = [p for p in DST_FILES if p != DST_FILES[0]] or DST_FILES
    for mode in ("flat", "shaded", "soft", "lit"):
        _load(proofer_page, DST_FILES[0])
        _set_mode(proofer_page, mode)
        _load(proofer_page, others[0])  # the second load is the regression
        scale = proofer_page.evaluate("() => window.__proofer.state.scale")
        assert scale > 0.01, f"mode {mode}: fit collapsed to scale {scale} on second load"
        img = _canvas_shot(proofer_page)
        assert ink_fraction(ink_mask(img.resize((300, 300)), WHITE)) > 0.01, (
            f"mode {mode}: blank canvas after loading a second design"
        )
    _set_mode(proofer_page, "shaded")


def test_no_js_errors_accumulated(proofer_page):
    assert proofer_page.js_errors == [], f"JS errors during session: {proofer_page.js_errors}"
