"""Proof layer 4 — renderers D and E verified in a real (headless) browser.

Playwright drives the actual bake-off UI: select a DST, wait for the client
panels to paint, then assert on the pixels — not blank, fabric where fabric
belongs, ink shape consistent with renderer B's server-side render of the
same design — and that the interactivity actually does something (zoom, pan,
hover-highlight, tilt all change pixels).

Caveat recorded in VERIFICATION.md: headless Chromium renders WebGL through
SwiftShader (software). These tests prove correctness, not GPU performance.

Skips cleanly when sample DSTs or Chromium are unavailable.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from pocs.poc1_dst_renderer.src.renderers import b_pillow
from pocs.poc1_dst_renderer.tests.conftest import (
    DST_FILES,
    color_distance,
    ink_fraction,
    ink_mask,
    mask_iou,
    normalized_mask,
)
from shared.design_colors import fabric_rgb

pytestmark = pytest.mark.skipif(
    not DST_FILES, reason="no sample DSTs in data/sample_dsts/ (gitignored)"
)

WHITE = fabric_rgb("white")
NAVY = fabric_rgb("navy")
# The multi-block test design: 5 colors, ink at the design centre.
MULTI = "000021273.DST"
# E's 3D look diverges from flat renders more than D's; floors measured
# per-renderer (D ~0.8+, E ~0.65+ against B) with safety margin.
IOU_FLOOR_D = 0.55
IOU_FLOOR_E = 0.45


def _shot(page, selector: str) -> Image.Image:
    return Image.open(io.BytesIO(page.locator(selector).screenshot())).convert("RGB")


def _select(page, base_url: str, dst_name: str) -> None:
    if page.url.rstrip("/") != base_url.rstrip("/"):
        page.goto(base_url)
    page.wait_for_selector(".dst-item")
    # Hide the timing badge: it overlays the canvas and would poison the ink
    # masks with dark pixels. (Duplicate style tags across calls are harmless.)
    page.add_style_tag(content=".timing { display: none !important; }")
    item = page.locator(".dst-item", has_text=dst_name)
    if item.count() == 0:
        pytest.skip(f"{dst_name} not in this corpus")
    item.click()
    for rid in ("d", "e"):
        page.wait_for_selector(
            f'.renderer[data-renderer="{rid}"] .render-area[data-rendered="1"]',
            timeout=30000,
        )
    page.wait_for_timeout(400)


def _canvas(page, rid: str) -> Image.Image:
    # Screenshot the render-area, not the canvas element: the canvas can
    # overflow its container by a sub-pixel, which element screenshots show
    # as a black band along the clipped edge.
    return _shot(page, f'.renderer[data-renderer="{rid}"] .render-area')


def test_page_boots_with_no_js_errors(browser_page, live_server):
    browser_page.goto(live_server)
    browser_page.wait_for_selector(".dst-item")
    browser_page.wait_for_selector(".fabric-swatch")
    assert browser_page.js_errors == [], f"JS errors on boot: {browser_page.js_errors}"


@pytest.mark.parametrize("rid", ["d", "e"])
def test_panel_paints_ink_on_fabric(browser_page, live_server, rid):
    _select(browser_page, live_server, MULTI)
    img = _canvas(browser_page, rid)
    mask = ink_mask(img, WHITE)
    assert ink_fraction(mask) > 0.05, f"renderer {rid} canvas is (nearly) blank"
    # Corners are outside the fitted design: must be fabric-ish. Probe 12px
    # in from each corner — the render-area has a border-radius whose clip
    # antialiases against the panel background at the very corner pixels.
    px = img.load()
    for corner in [(12, 12), (img.width - 13, 12), (12, img.height - 13)]:
        assert color_distance(px[corner], WHITE) < 60, (
            f"renderer {rid} corner {corner} is {px[corner]}, expected near-white fabric"
        )


@pytest.mark.parametrize("rid,floor", [("d", IOU_FLOOR_D), ("e", IOU_FLOOR_E)])
def test_browser_render_matches_server_geometry(browser_page, live_server, rid, floor):
    """Cross-renderer consistency, browser edition: D/E ink masks must agree
    with renderer B's server-side render of the same design."""
    _select(browser_page, live_server, MULTI)
    dst_path = next(p for p in DST_FILES if p.name == MULTI)
    ref = Image.open(io.BytesIO(b_pillow.render_png(dst_path, fabric=WHITE))).convert("RGB")
    ref_mask = normalized_mask(ink_mask(ref.resize((400, 400)), WHITE))

    img = _canvas(browser_page, rid)
    got_mask = normalized_mask(ink_mask(img, WHITE))
    iou = mask_iou(ref_mask, got_mask)
    assert iou >= floor, (
        f"renderer {rid} ink mask disagrees with server renderer B (IoU {iou:.3f} < {floor})"
    )


@pytest.mark.parametrize("rid", ["d", "e"])
def test_wheel_zoom_changes_pixels(browser_page, live_server, rid):
    _select(browser_page, live_server, MULTI)
    sel = f'.renderer[data-renderer="{rid}"] .render-area canvas'
    before = _shot(browser_page, sel)
    box = browser_page.locator(sel).bounding_box()
    browser_page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    browser_page.mouse.wheel(0, -480)
    browser_page.wait_for_timeout(400)
    after = _shot(browser_page, sel)
    assert list(before.getdata()) != list(after.getdata()), f"{rid}: zoom did not repaint"


@pytest.mark.parametrize("rid", ["d", "e"])
def test_drag_pan_changes_pixels(browser_page, live_server, rid):
    _select(browser_page, live_server, MULTI)
    sel = f'.renderer[data-renderer="{rid}"] .render-area canvas'
    before = _shot(browser_page, sel)
    box = browser_page.locator(sel).bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    browser_page.mouse.move(cx, cy)
    browser_page.mouse.down()
    browser_page.mouse.move(cx + 60, cy + 35, steps=5)
    browser_page.mouse.up()
    browser_page.wait_for_timeout(400)
    after = _shot(browser_page, sel)
    assert list(before.getdata()) != list(after.getdata()), f"{rid}: pan did not repaint"


def test_hover_highlights_color_block_in_d(browser_page, live_server):
    """D's POC 3 rehearsal: hovering a block dims the others."""
    _select(browser_page, live_server, MULTI)
    sel = '.renderer[data-renderer="d"] .render-area canvas'
    box = browser_page.locator(sel).bounding_box()
    # Hover dead centre (the monogram — known ink for this design).
    browser_page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    browser_page.wait_for_timeout(400)
    hovered = _shot(browser_page, sel)
    # Move off-canvas: highlight clears.
    browser_page.mouse.move(box["x"] - 40, box["y"] - 40)
    browser_page.wait_for_timeout(400)
    cleared = _shot(browser_page, sel)
    assert list(hovered.getdata()) != list(cleared.getdata()), (
        "hovering an inked block changed nothing — highlight is not working"
    )


def test_tilt_changes_pixels_in_e(browser_page, live_server):
    """E's 2.5D payoff: shift-drag tilts the camera."""
    _select(browser_page, live_server, MULTI)
    sel = '.renderer[data-renderer="e"] .render-area canvas'
    before = _shot(browser_page, sel)
    box = browser_page.locator(sel).bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    browser_page.keyboard.down("Shift")
    browser_page.mouse.move(cx, cy)
    browser_page.mouse.down()
    browser_page.mouse.move(cx, cy + 80, steps=5)
    browser_page.mouse.up()
    browser_page.keyboard.up("Shift")
    browser_page.wait_for_timeout(400)
    after = _shot(browser_page, sel)
    assert list(before.getdata()) != list(after.getdata()), "shift-drag tilt did not repaint"


def test_fabric_switch_updates_client_panels(browser_page, live_server):
    _select(browser_page, live_server, MULTI)
    browser_page.locator('.fabric-swatch[data-fabric="navy"]').click()
    browser_page.wait_for_timeout(800)
    try:
        for rid in ("d", "e"):
            img = _canvas(browser_page, rid)
            corner = img.load()[12, 12]
            assert color_distance(corner, NAVY) < 60, (
                f"renderer {rid} corner is {corner} after switching to navy fabric"
            )
    finally:
        # Restore default so test order never matters.
        browser_page.locator('.fabric-swatch[data-fabric="white"]').click()
        browser_page.wait_for_timeout(400)


def test_no_js_errors_accumulated(browser_page, live_server):
    """Runs last in file order: nothing above may have thrown in the page."""
    assert browser_page.js_errors == [], f"JS errors during session: {browser_page.js_errors}"
