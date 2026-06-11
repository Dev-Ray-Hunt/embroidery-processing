"""Renderer B — Pillow 2D with angle-based thread shading.

Custom raster renderer: every stitch is a thick line whose brightness depends
on its angle, simulating directional light catching thread luster — horizontal
stitches read bright, vertical ones darker, so fill direction stays visible
(a POC pass/fail criterion). Pillow's line drawing has no antialiasing, so we
render at 2x and downsample with Lanczos.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from pocs.poc1_dst_renderer.src import design_geometry, dst_parser
from shared.design_colors import DEFAULT_FABRIC, block_color, fabric_rgb

SUPERSAMPLE = 2
# Brightness multiplier range across stitch angles: 0° (horizontal) maps to
# BRIGHT, 90° (vertical) to DARK. The swing is deliberately strong enough to
# survive downsampling — subtle shading vanished in early experiments.
SHADE_BRIGHT = 1.18
SHADE_DARK = 0.72


def _shade(rgb: tuple[int, int, int], angle_rad: float) -> tuple[int, int, int]:
    """Scale a color's brightness by stitch angle (0 = horizontal = brightest)."""
    # cos^2 folds the angle symmetrically: 0 and 180 degrees shade identically.
    t = math.cos(angle_rad) ** 2
    k = SHADE_DARK + (SHADE_BRIGHT - SHADE_DARK) * t
    return tuple(min(255, max(0, round(c * k))) for c in rgb)  # type: ignore[return-value]


def render_design(
    design: dst_parser.ParsedDesign,
    *,
    fabric: tuple[int, int, int] | None = None,
    palette: list[tuple[int, int, int]] | None = None,
    max_dim: int = 1000,
) -> Image.Image:
    """Render a parsed design to a PIL Image on a solid fabric background."""
    fabric = fabric or fabric_rgb(DEFAULT_FABRIC)
    lay = design_geometry.layout(design, max_dim=max_dim * SUPERSAMPLE)

    img = Image.new("RGB", (lay.width, lay.height), fabric)
    draw = ImageDraw.Draw(img)
    width_px = max(1, round(lay.thread_width_px))

    for block in lay.blocks:
        base = block_color(block.index, palette)
        for seg in block.segments:
            angle = math.atan2(seg.y1 - seg.y0, seg.x1 - seg.x0)
            draw.line(
                [(seg.x0, seg.y0), (seg.x1, seg.y1)],
                fill=_shade(base, angle),
                width=width_px,
            )

    return img.resize((lay.width // SUPERSAMPLE, lay.height // SUPERSAMPLE), Image.LANCZOS)


def render_png(
    dst_path: Path,
    *,
    fabric: tuple[int, int, int] | None = None,
    palette: list[tuple[int, int, int]] | None = None,
) -> bytes:
    """File-path entry point used by the bake-off server."""
    import io

    design = dst_parser.parse(dst_path)
    img = render_design(design, fabric=fabric, palette=palette)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
