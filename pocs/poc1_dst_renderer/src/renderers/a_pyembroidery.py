"""Renderer A — pyembroidery's built-in PNG writer.

Zero custom rendering code. Baseline bake-off entry: whatever pyembroidery's
PngWriter produces out of the box, that's what this returns. The point is to
have a no-effort floor to compare every other renderer against.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pyembroidery


def render_png(dst_path: Path) -> bytes:
    """Render a DST file to PNG bytes via pyembroidery's PngWriter.

    pyembroidery.write_png writes to a file path (no in-memory stream API),
    so we round-trip through a NamedTemporaryFile. The temp file is cleaned
    up before returning regardless of success.
    """
    pattern = pyembroidery.read(str(dst_path))
    if pattern is None:
        raise ValueError(f"pyembroidery could not read {dst_path}")

    tmp_path = Path(tempfile.mktemp(suffix=".png"))
    try:
        pyembroidery.write_png(pattern, str(tmp_path))
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)
