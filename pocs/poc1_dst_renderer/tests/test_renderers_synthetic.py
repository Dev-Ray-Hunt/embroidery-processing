"""Proof layer 1 — synthetic fixtures with knowable correct output.

These run with no sample data at all: tiny hand-built designs where we can
say exactly which regions must contain thread ink, which must stay fabric,
and which colors must appear. Applied to the server-side custom renderers
(B Pillow, C Cairo) via their design-level entry points.
"""

from __future__ import annotations

import io

import pytest

from pocs.poc1_dst_renderer.src.renderers import b_pillow, c_cairo
from pocs.poc1_dst_renderer.tests.conftest import (
    color_distance,
    dense_line,
    has_color_near,
    ink_fraction,
    ink_mask,
    make_design,
)
from shared.design_colors import DEFAULT_THREAD_PALETTE, fabric_rgb

FABRIC = fabric_rgb("white")


def render(renderer: str, design, **kw) -> Image.Image:  # noqa: F821
    if renderer == "b":
        return b_pillow.render_design(design, fabric=FABRIC, **kw)
    surface = c_cairo.render_design_to_surface(design, fabric=FABRIC, **kw)
    buf = io.BytesIO()
    surface.write_to_png(buf)
    from PIL import Image

    return Image.open(buf).convert("RGB")


# A hollow square outline, single color block. The frame must be inked; the
# centre and the corners of the canvas must stay fabric.
SQUARE = make_design(
    [
        *dense_line(0, 0, 100, 0),
        *dense_line(100, 0, 100, 100),
        *dense_line(100, 100, 0, 100),
        *dense_line(0, 100, 0, 0),
    ]
)

# Two horizontal bars: block 0 on top, COLOR_CHANGE, block 1 below.
TWO_BLOCKS = make_design(
    [
        *dense_line(0, 0, 100, 0),
        (100, 0, "COLOR_CHANGE"),
        *dense_line(100, 60, 0, 60),
    ]
)

# Two bars separated by a JUMP — the gap between them must NOT be drawn.
JUMP_GAP = make_design(
    [
        *dense_line(0, 0, 40, 0),
        (100, 0, "JUMP"),
        *dense_line(100, 0, 140, 0),
    ]
)


@pytest.mark.parametrize("renderer", ["b", "c"])
def test_square_outline_inks_frame_not_centre(renderer):
    img = render(renderer, SQUARE)
    mask = ink_mask(img, FABRIC)
    px = mask.load()
    w, h = mask.size

    assert ink_fraction(mask) > 0.02, "square outline produced almost no ink"
    # Centre must be fabric (the square is hollow).
    assert px[w // 2, h // 2] == 0, "centre of hollow square was inked"
    # Frame must be inked: probe the four edge midpoints of the ink bbox.
    bbox = mask.getbbox()
    assert bbox is not None
    x0, y0, x1, y1 = bbox
    midx, midy = (x0 + x1) // 2, (y0 + y1) // 2
    assert px[midx, y0 + 2] == 255, "top edge not inked"
    assert px[midx, y1 - 3] == 255, "bottom edge not inked"
    assert px[x0 + 2, midy] == 255, "left edge not inked"
    assert px[x1 - 3, midy] == 255, "right edge not inked"
    # Canvas corners are margin — must be fabric.
    assert px[0, 0] == 0 and px[w - 1, h - 1] == 0, "margin corners were inked"


@pytest.mark.parametrize("renderer", ["b", "c"])
def test_color_change_switches_thread_color(renderer):
    img = render(renderer, TWO_BLOCKS)
    # Both palette colors must appear...
    assert has_color_near(img, DEFAULT_THREAD_PALETTE[0]), "block 0 color missing"
    assert has_color_near(img, DEFAULT_THREAD_PALETTE[1]), "block 1 color missing"
    # ...and in the right vertical order: block 0's bar is the TOP one.
    px = img.load()
    w, h = img.size

    def row_color(frac_y):
        # Dominant non-fabric color across a row through one bar.
        best, best_d = None, -1.0
        for x in range(0, w, 2):
            c = px[x, int(h * frac_y)]
            d = color_distance(c, FABRIC)
            if d > best_d:
                best, best_d = c, d
        return best

    top = row_color(0.08)
    bottom = row_color(0.92)
    assert color_distance(top, DEFAULT_THREAD_PALETTE[0]) < color_distance(
        top, DEFAULT_THREAD_PALETTE[1]
    ), "top bar is not block 0's color"
    assert color_distance(bottom, DEFAULT_THREAD_PALETTE[1]) < color_distance(
        bottom, DEFAULT_THREAD_PALETTE[0]
    ), "bottom bar is not block 1's color"


@pytest.mark.parametrize("renderer", ["b", "c"])
def test_jump_leaves_gap_undrawn(renderer):
    img = render(renderer, JUMP_GAP)
    mask = ink_mask(img, FABRIC)
    px = mask.load()
    w, h = mask.size
    # The design is a 140-unit-wide strip; the jump spans x=40..100 (i.e. the
    # middle ~43% of the width). Probe the dead centre of the gap.
    bbox = mask.getbbox()
    assert bbox is not None
    x0, _, x1, _ = bbox
    gap_x = x0 + (x1 - x0) // 2
    midy = h // 2
    assert px[gap_x, midy] == 0, "jump gap was drawn as thread"
    # But both bars exist: ink near both ends.
    assert px[x0 + 3, midy] == 255, "left bar missing"
    assert px[x1 - 4, midy] == 255, "right bar missing"


@pytest.mark.parametrize("renderer", ["b", "c"])
@pytest.mark.parametrize("fabric_name", ["white", "black", "navy"])
def test_fabric_color_fills_background(renderer, fabric_name):
    fabric = fabric_rgb(fabric_name)
    if renderer == "b":
        img = b_pillow.render_design(SQUARE, fabric=fabric)
    else:
        surface = c_cairo.render_design_to_surface(SQUARE, fabric=fabric)
        buf = io.BytesIO()
        surface.write_to_png(buf)
        from PIL import Image

        img = Image.open(buf).convert("RGB")
    px = img.load()
    for corner in [
        (0, 0),
        (img.width - 1, 0),
        (0, img.height - 1),
        (img.width - 1, img.height - 1),
    ]:
        assert color_distance(px[corner], fabric) < 12, (
            f"corner {corner} is not {fabric_name} fabric"
        )


def test_angle_shading_differs_horizontal_vs_vertical():
    """Renderer B's defining feature: stitch angle modulates brightness."""
    horiz = make_design(dense_line(0, 0, 100, 0))
    vert = make_design(dense_line(0, 0, 0, 100))
    img_h = b_pillow.render_design(horiz, fabric=FABRIC)
    img_v = b_pillow.render_design(vert, fabric=FABRIC)

    def mean_ink_brightness(img):
        mask = ink_mask(img, FABRIC)
        mpx, ipx = mask.load(), img.load()
        tot = n = 0
        for y in range(img.height):
            for x in range(img.width):
                if mpx[x, y]:
                    tot += sum(ipx[x, y])
                    n += 1
        return tot / (3 * n)

    bh, bv = mean_ink_brightness(img_h), mean_ink_brightness(img_v)
    assert bh > bv * 1.15, (
        f"horizontal stitches ({bh:.0f}) should be visibly brighter than vertical ({bv:.0f})"
    )
