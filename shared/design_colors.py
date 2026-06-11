"""Canonical thread palette and fabric backgrounds for the POCs.

DST files carry no thread-color data — only color-change events — and the real
Madeira mapping is POC 2's job. Until that exists, every renderer assigns the
same deterministic default palette by color-block index, so the five bake-off
panels stay directly comparable. Renderers accept a palette override so POC 3
can inject real thread colors later without touching renderer code.

Colors are (R, G, B) tuples, 0-255.
"""

from __future__ import annotations

# Embroidery-plausible thread colors, ordered for maximum adjacent contrast so
# consecutive blocks in a design never blur together. Index 0 is deliberately
# not white/black: most single-color tests happen on the white fabric.
DEFAULT_THREAD_PALETTE: list[tuple[int, int, int]] = [
    (27, 63, 148),  # royal blue
    (200, 16, 46),  # scarlet
    (255, 199, 44),  # gold
    (255, 255, 255),  # white
    (16, 24, 32),  # near-black
    (0, 121, 52),  # emerald
    (243, 115, 33),  # orange
    (93, 35, 139),  # purple
    (137, 141, 141),  # silver gray
    (114, 47, 55),  # maroon
    (0, 156, 166),  # teal
    (246, 141, 169),  # pink
    (84, 98, 35),  # olive
    (153, 102, 51),  # tan / bronze
    (173, 216, 230),  # light blue
    (255, 240, 165),  # pale yellow
    (54, 57, 74),  # slate navy
    (188, 32, 75),  # raspberry
    (140, 196, 116),  # sage
    (94, 73, 52),  # brown
]

# The three POC fabric backgrounds (solid colors — see POC 1 spec; texture is
# explicitly out of scope). White is a warm off-white so pale threads stay
# visible against it.
FABRICS: dict[str, tuple[int, int, int]] = {
    "white": (242, 241, 236),  # white piqué
    "black": (28, 28, 30),  # black twill
    "navy": (35, 47, 75),  # navy twill
}

DEFAULT_FABRIC = "white"


def block_color(
    index: int, palette: list[tuple[int, int, int]] | None = None
) -> tuple[int, int, int]:
    """Thread color for color-block `index`, cycling if the design has more
    blocks than the palette has entries."""
    p = palette or DEFAULT_THREAD_PALETTE
    return p[index % len(p)]


def fabric_rgb(name: str) -> tuple[int, int, int]:
    """Resolve a fabric name to RGB. Raises KeyError on unknown names so the
    API layer can turn it into a 400 rather than silently defaulting."""
    return FABRICS[name]
