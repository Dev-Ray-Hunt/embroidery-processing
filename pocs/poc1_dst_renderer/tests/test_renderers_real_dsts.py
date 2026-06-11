"""Proof layers 2 + 3 — real sample DSTs through the server-side renderers.

Layer 2 (cross-renderer consistency): A, B and C all draw the same geometry,
styled differently. Normalized ink-mask IoU between every pair must clear a
floor that coordinate-transform bugs cannot. Measured baselines (2026-06-10):
correct renders score 0.64-0.99 across the 7-file corpus; a deliberately
Y-flipped render scores 0.10-0.41. Floor set at 0.55.

Layer 3 (property checks): output aspect ratio matches the design extents,
every palette block color actually appears, fabric fills the corners, and
renders meet the POC's hard speed bar.

Skips cleanly when data/sample_dsts/ is empty (files are gitignored).
"""

from __future__ import annotations

import io
import time

import pytest
from PIL import Image

from pocs.poc1_dst_renderer.src import dst_parser
from pocs.poc1_dst_renderer.src.renderers import a_pyembroidery, b_pillow, c_cairo
from pocs.poc1_dst_renderer.tests.conftest import (
    DST_FILES,
    color_distance,
    has_color_near,
    ink_mask,
    mask_iou,
    normalized_mask,
)
from shared.design_colors import block_color, fabric_rgb

pytestmark = pytest.mark.skipif(
    not DST_FILES, reason="no sample DSTs in data/sample_dsts/ (gitignored)"
)

FABRIC = fabric_rgb("white")
IOU_FLOOR = 0.55
_ids = [p.name for p in DST_FILES]


def _render(renderer_id: str, dst_path) -> Image.Image:
    if renderer_id == "a":
        raw = a_pyembroidery.render_png(dst_path)
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        bg = Image.new("RGBA", img.size, (*FABRIC, 255))
        return Image.alpha_composite(bg, img).convert("RGB")
    if renderer_id == "b":
        return Image.open(io.BytesIO(b_pillow.render_png(dst_path, fabric=FABRIC))).convert("RGB")
    return Image.open(io.BytesIO(c_cairo.render_png(dst_path, fabric=FABRIC))).convert("RGB")


def _norm_mask(img: Image.Image) -> Image.Image:
    # Downscale before per-pixel work; shape comparison doesn't need 1000px.
    small = img.resize((min(400, img.width), min(400, img.height)))
    return normalized_mask(ink_mask(small, FABRIC))


@pytest.mark.parametrize("dst_path", DST_FILES, ids=_ids)
def test_cross_renderer_consistency(dst_path):
    masks = {rid: _norm_mask(_render(rid, dst_path)) for rid in ("a", "b", "c")}
    for pair in (("a", "b"), ("a", "c"), ("b", "c")):
        iou = mask_iou(masks[pair[0]], masks[pair[1]])
        assert iou >= IOU_FLOOR, (
            f"{pair[0].upper()} vs {pair[1].upper()} ink masks disagree on {dst_path.name} "
            f"(IoU {iou:.3f} < {IOU_FLOOR}) — likely a coordinate/scale bug in one of them"
        )


@pytest.mark.parametrize("renderer_id", ["b", "c"])
@pytest.mark.parametrize("dst_path", DST_FILES, ids=_ids)
def test_aspect_ratio_matches_extents(renderer_id, dst_path):
    design = dst_parser.parse(dst_path)
    min_x, min_y, max_x, max_y = design.extents
    design_aspect = (max_x - min_x) / max(max_y - min_y, 1e-6)

    img = _render(renderer_id, dst_path)
    mask = ink_mask(img.resize((min(400, img.width), min(400, img.height))), FABRIC)
    bbox = mask.getbbox()
    assert bbox is not None, "render produced no ink at all"
    # Ink bbox aspect in original pixel space.
    sx = img.width / mask.width
    sy = img.height / mask.height
    ink_aspect = ((bbox[2] - bbox[0]) * sx) / max((bbox[3] - bbox[1]) * sy, 1e-6)
    assert ink_aspect == pytest.approx(design_aspect, rel=0.12), (
        f"ink bbox aspect {ink_aspect:.2f} vs design extents aspect {design_aspect:.2f}"
    )


@pytest.mark.parametrize("renderer_id", ["b", "c"])
@pytest.mark.parametrize("dst_path", DST_FILES, ids=_ids)
def test_every_block_color_appears(renderer_id, dst_path):
    design = dst_parser.parse(dst_path)
    img = _render(renderer_id, dst_path)
    missing = []
    for i in range(design.metadata["color_block_count"]):
        # Tolerance covers B's angle shading (up to ±28% brightness swing)
        # and C's alpha-over-fabric blend.
        if not has_color_near(img, block_color(i), tol=90):
            missing.append(i)
    assert not missing, f"palette colors for blocks {missing} never appear in the render"


@pytest.mark.parametrize("renderer_id", ["b", "c"])
@pytest.mark.parametrize("dst_path", DST_FILES, ids=_ids)
def test_fabric_at_corners(renderer_id, dst_path):
    img = _render(renderer_id, dst_path)
    px = img.load()
    for corner in [
        (0, 0),
        (img.width - 1, 0),
        (0, img.height - 1),
        (img.width - 1, img.height - 1),
    ]:
        assert color_distance(px[corner], FABRIC) < 12, f"corner {corner} is not fabric"


def test_render_speed_meets_poc_bar():
    """POC pass/fail: < 10 s for a 20k-stitch design. Use the biggest design
    present (63k stitches when the team corpus is in place) for headroom."""
    biggest = max(DST_FILES, key=lambda p: dst_parser.parse(p).metadata["stitch_count"])
    for renderer_id in ("b", "c"):
        t0 = time.perf_counter()
        _render(renderer_id, biggest)
        elapsed = time.perf_counter() - t0
        assert elapsed < 10, f"renderer {renderer_id} took {elapsed:.1f}s on {biggest.name}"
