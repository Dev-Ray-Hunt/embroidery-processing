"""Stub interface for DST parse integration (POC 1) and color-up editor (POC 3).

These integrations are local-only — DST files and the POC 3 editor are not
available in the cloud sandbox.  All functions here raise NotImplementedError
so that any accidental call fails loudly rather than silently.

To wire up real DST parsing, replace the bodies of these functions with calls
to pocs.poc1_dst_renderer (once POC 1 is importable in the runtime environment).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class DSTNotAvailableError(NotImplementedError):
    """Raised in the cloud sandbox when DST parsing is attempted."""


def parse_dst(dst_path: Path) -> dict[str, Any]:
    """Parse a DST file and return structured design metadata.

    Stub — not implemented in the cloud.  In production this delegates to
    pocs.poc1_dst_renderer.

    Expected return shape::

        {
            "stitch_count": int,
            "color_count": int,
            "width_mm": float,
            "height_mm": float,
            "stop_count": int,
            "trim_count": int,
            "stops": [{"stop": int, "stitch_count": int}, ...],
        }
    """
    raise DSTNotAvailableError(
        "DST parsing is not available in the cloud sandbox.  "
        "Wire up pocs.poc1_dst_renderer locally."
    )


def open_color_up_editor(logo_id: int, colorup_id: int | None = None) -> None:
    """Open the POC 3 color-up editor for the given logo.

    Stub — not implemented in the cloud.
    """
    raise DSTNotAvailableError("The color-up editor (POC 3) is not available in the cloud sandbox.")
