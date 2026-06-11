"""DST parser — the shared front-end every POC 1 renderer consumes.

Parse once here, render five ways. A DST file goes in; a small, explicit,
JSON-serializable structure comes out (see SCHEMA.md). The bake-off web UI and
all five renderers read *this* structure rather than calling pyembroidery
directly, so the parsing logic lives in exactly one place.

CLI:

    uv run python -m pocs.poc1_dst_renderer.src.dst_parser <path-to-dst>
    uv run python -m pocs.poc1_dst_renderer.src.dst_parser <path-to-dst> --summary

The bare form prints the full parsed JSON (stitches included); --summary prints
just the metadata block, which is what the file-list view needs.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pyembroidery

# Low byte of pyembroidery's command int -> canonical command name. pyembroidery
# may OR flag bits above the low byte, so we mask with COMMAND_MASK before
# looking the command up. Anything unmapped is surfaced as CMD_<n> rather than
# silently dropped, so a renderer can decide what to do with it.
_COMMAND_NAMES: dict[int, str] = {
    pyembroidery.STITCH: "STITCH",
    pyembroidery.JUMP: "JUMP",
    pyembroidery.TRIM: "TRIM",
    pyembroidery.STOP: "STOP",
    pyembroidery.END: "END",
    pyembroidery.COLOR_CHANGE: "COLOR_CHANGE",
    pyembroidery.SEQUIN_MODE: "SEQUIN_MODE",
    pyembroidery.SEQUIN_EJECT: "SEQUIN_EJECT",
    pyembroidery.NEEDLE_SET: "NEEDLE_SET",
}


def _command_name(raw: int) -> str:
    base = raw & pyembroidery.COMMAND_MASK
    return _COMMAND_NAMES.get(base, f"CMD_{base}")


@dataclass
class ParsedDesign:
    """Normalized DST contents. See SCHEMA.md for the JSON shape.

    Coordinates and extents are in native DST units (0.1 mm); width_mm /
    height_mm in `metadata` are the human-facing millimeter conversions.
    """

    source: str
    stitches: list[tuple[float, float, str]]
    color_change_indices: list[int]
    extents: tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    metadata: dict

    def to_dict(self) -> dict:
        """Full canonical structure, JSON-serializable."""
        return {
            "source": self.source,
            "metadata": self.metadata,
            "extents": list(self.extents),
            "color_change_indices": self.color_change_indices,
            "stitches": [[x, y, cmd] for (x, y, cmd) in self.stitches],
        }

    def summary(self) -> dict:
        """Metadata-only view for the file list (no per-stitch payload)."""
        return {"source": self.source, **self.metadata}


def parse(dst_path: str | Path) -> ParsedDesign:
    """Parse a DST file into a `ParsedDesign`.

    Raises ValueError if pyembroidery cannot read the file.
    """
    dst_path = Path(dst_path)
    pattern = pyembroidery.read(str(dst_path))
    if pattern is None:
        raise ValueError(f"pyembroidery could not read {dst_path}")

    stitches: list[tuple[float, float, str]] = []
    color_change_indices: list[int] = []
    counts = {
        "STITCH": 0,
        "JUMP": 0,
        "TRIM": 0,
        "COLOR_CHANGE": 0,
    }
    for x, y, command in pattern.stitches:
        name = _command_name(command)
        if name == "COLOR_CHANGE":
            color_change_indices.append(len(stitches))
        if name in counts:
            counts[name] += 1
        stitches.append((x, y, name))

    extents = pattern.extents()  # (min_x, min_y, max_x, max_y) in 0.1mm units
    min_x, min_y, max_x, max_y = extents

    metadata = {
        # STITCH commands only — matches the count Wilcom and other tools report.
        "stitch_count": counts["STITCH"],
        # Every entry in the stitch list, including jumps/trims/color-changes/end.
        "command_count": len(stitches),
        "jump_count": counts["JUMP"],
        "trim_count": counts["TRIM"],
        "color_change_count": counts["COLOR_CHANGE"],
        # DST stores no thread metadata, so blocks = color changes + 1.
        "color_block_count": counts["COLOR_CHANGE"] + 1,
        "width_mm": round((max_x - min_x) / 10, 1),
        "height_mm": round((max_y - min_y) / 10, 1),
    }

    return ParsedDesign(
        source=dst_path.name,
        stitches=stitches,
        color_change_indices=color_change_indices,
        extents=(min_x, min_y, max_x, max_y),
        metadata=metadata,
    )


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parse a DST file to canonical JSON.")
    ap.add_argument("dst_path", type=Path, help="Path to a .dst file")
    ap.add_argument(
        "--summary",
        action="store_true",
        help="Print only the metadata block (omit the per-stitch payload).",
    )
    args = ap.parse_args(argv)

    try:
        design = parse(args.dst_path)
    except (ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    payload = design.summary() if args.summary else design.to_dict()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
