"""Shared geometry for the server-side custom renderers (B, C).

Turns a ParsedDesign into per-color-block polyline segments in pixel space,
with a fit-to-canvas transform. Keeping the transform in one place means B and
C differ only in how they *draw* — exactly what the bake-off wants to compare.
(Renderer A and the browser renderers keep fully independent transforms, which
preserves the cross-renderer consistency check's power.)

Parsed coordinates are screen-oriented (+y down) — verified empirically against
renderer A's output (IoU 0.95 on star.dst with +y-down vs 0.41 flipped), so no
axis flip happens here.
"""

from __future__ import annotations

from dataclasses import dataclass

from pocs.poc1_dst_renderer.src.dst_parser import ParsedDesign

# 1 DST unit = 0.1 mm. Thread is ~0.4 mm wide => 4 DST units.
THREAD_WIDTH_DST_UNITS = 4.0


@dataclass
class Segment:
    """One drawn stitch: a line from (x0, y0) to (x1, y1) in pixel space."""

    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class ColorBlock:
    """All segments stitched with one thread color."""

    index: int
    segments: list[Segment]


@dataclass
class PixelLayout:
    """A design fitted into a pixel canvas."""

    width: int
    height: int
    blocks: list[ColorBlock]
    px_per_unit: float

    @property
    def thread_width_px(self) -> float:
        return THREAD_WIDTH_DST_UNITS * self.px_per_unit


def layout(design: ParsedDesign, *, max_dim: int = 1000, margin_frac: float = 0.04) -> PixelLayout:
    """Fit `design` into a canvas whose longest side is `max_dim` pixels.

    Aspect ratio is preserved; `margin_frac` of the longest side is left as
    border on every edge. STITCH commands become segments from the previous
    point; JUMP / TRIM / COLOR_CHANGE move the pen without drawing, and
    COLOR_CHANGE additionally starts the next block.
    """
    min_x, min_y, max_x, max_y = design.extents
    w_units = max(max_x - min_x, 1e-6)
    h_units = max(max_y - min_y, 1e-6)

    margin = max_dim * margin_frac
    scale = (max_dim - 2 * margin) / max(w_units, h_units)
    width = int(round(w_units * scale + 2 * margin))
    height = int(round(h_units * scale + 2 * margin))

    def to_px(x: float, y: float) -> tuple[float, float]:
        return (margin + (x - min_x) * scale, margin + (y - min_y) * scale)

    blocks: list[ColorBlock] = [ColorBlock(index=0, segments=[])]
    prev: tuple[float, float] | None = None
    for x, y, cmd in design.stitches:
        pt = to_px(x, y)
        if cmd == "STITCH":
            if prev is not None:
                blocks[-1].segments.append(Segment(prev[0], prev[1], pt[0], pt[1]))
            prev = pt
        elif cmd == "COLOR_CHANGE":
            blocks.append(ColorBlock(index=len(blocks), segments=[]))
            prev = pt
        else:
            # JUMP / TRIM / STOP / END / anything exotic: move, don't draw.
            prev = pt

    return PixelLayout(width=width, height=height, blocks=blocks, px_per_unit=scale)
