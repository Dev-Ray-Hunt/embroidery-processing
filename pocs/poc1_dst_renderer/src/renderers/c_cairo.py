"""Renderer C — PyCairo antialiased vector rendering.

Cairo draws each stitch as a stroked path with round caps and full
antialiasing — the bake-off's "smooth professional 2D" entry. Stitches are
drawn at slightly reduced opacity so overlapping passes build up density the
way real thread coverage does; a second, thinner bright pass down each
stitch's center suggests thread sheen without per-pixel shading.
"""

from __future__ import annotations

import io
import math
from pathlib import Path

import cairo

from pocs.poc1_dst_renderer.src import design_geometry, dst_parser
from shared.design_colors import DEFAULT_FABRIC, block_color, fabric_rgb

# Stitch body opacity: < 1.0 so dense fill regions visibly accumulate.
BODY_ALPHA = 0.85
# Sheen pass: a thin lighter stroke over the stitch center line.
SHEEN_ALPHA = 0.25
SHEEN_WIDTH_FRAC = 0.35


def render_design_to_surface(
    design: dst_parser.ParsedDesign,
    *,
    fabric: tuple[int, int, int] | None = None,
    palette: list[tuple[int, int, int]] | None = None,
    max_dim: int = 1000,
) -> cairo.ImageSurface:
    """Render a parsed design onto a Cairo image surface."""
    fabric = fabric or fabric_rgb(DEFAULT_FABRIC)
    lay = design_geometry.layout(design, max_dim=max_dim)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, lay.width, lay.height)
    ctx = cairo.Context(surface)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)

    ctx.set_source_rgb(*(c / 255 for c in fabric))
    ctx.paint()

    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    width = max(1.0, lay.thread_width_px)

    for block in lay.blocks:
        r, g, b = (c / 255 for c in block_color(block.index, palette))

        # Body pass: full-width, slightly translucent.
        ctx.set_line_width(width)
        ctx.set_source_rgba(r, g, b, BODY_ALPHA)
        for seg in block.segments:
            ctx.move_to(seg.x0, seg.y0)
            ctx.line_to(seg.x1, seg.y1)
            ctx.stroke()

        # Sheen pass: thin lighter line down the stitch center.
        ctx.set_line_width(max(0.5, width * SHEEN_WIDTH_FRAC))
        ctx.set_source_rgba(r + (1 - r) * 0.7, g + (1 - g) * 0.7, b + (1 - b) * 0.7, SHEEN_ALPHA)
        for seg in block.segments:
            # Skip near-zero-length stitches; the body pass dot covers them.
            if math.hypot(seg.x1 - seg.x0, seg.y1 - seg.y0) < 1.0:
                continue
            ctx.move_to(seg.x0, seg.y0)
            ctx.line_to(seg.x1, seg.y1)
            ctx.stroke()

    return surface


def render_png(
    dst_path: Path,
    *,
    fabric: tuple[int, int, int] | None = None,
    palette: list[tuple[int, int, int]] | None = None,
) -> bytes:
    """File-path entry point used by the bake-off server."""
    design = dst_parser.parse(dst_path)
    surface = render_design_to_surface(design, fabric=fabric, palette=palette)
    buf = io.BytesIO()
    surface.write_to_png(buf)
    return buf.getvalue()
