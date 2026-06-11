"""Internal-consistency checks for the DST parser.

No Wilcom ground truth exists (architectural isolation), so these validate the
parser against pyembroidery itself and against round-trip stability. DST sample
files are gitignored; tests skip cleanly when none are present (e.g. CI).
"""

from __future__ import annotations

import json
from pathlib import Path

import pyembroidery
import pytest

from pocs.poc1_dst_renderer.src import dst_parser

DST_DIR = Path(__file__).resolve().parents[3] / "data" / "sample_dsts"
# Case-insensitive: team-supplied files are named .DST.
DST_FILES = (
    sorted(p for p in DST_DIR.iterdir() if p.suffix.lower() == ".dst")
    if DST_DIR.exists()
    else []
)

pytestmark = pytest.mark.skipif(
    not DST_FILES, reason="no sample DSTs in data/sample_dsts/ (gitignored)"
)

# Make each DST show up as its own named test case.
_ids = [p.name for p in DST_FILES]


@pytest.mark.parametrize("dst_path", DST_FILES, ids=_ids)
def test_stitch_and_command_counts_match_pyembroidery(dst_path: Path) -> None:
    design = dst_parser.parse(dst_path)
    pattern = pyembroidery.read(str(dst_path))

    raw = pattern.stitches
    expected_stitches = sum(
        1 for s in raw if (s[2] & pyembroidery.COMMAND_MASK) == pyembroidery.STITCH
    )
    expected_color_changes = sum(
        1 for s in raw if (s[2] & pyembroidery.COMMAND_MASK) == pyembroidery.COLOR_CHANGE
    )

    assert design.metadata["command_count"] == len(raw)
    assert design.metadata["stitch_count"] == expected_stitches
    assert design.metadata["color_change_count"] == expected_color_changes
    assert design.metadata["color_block_count"] == expected_color_changes + 1


@pytest.mark.parametrize("dst_path", DST_FILES, ids=_ids)
def test_extents_match_pyembroidery(dst_path: Path) -> None:
    design = dst_parser.parse(dst_path)
    pattern = pyembroidery.read(str(dst_path))
    assert tuple(design.extents) == tuple(pattern.extents())


@pytest.mark.parametrize("dst_path", DST_FILES, ids=_ids)
def test_color_change_indices_point_at_color_changes(dst_path: Path) -> None:
    design = dst_parser.parse(dst_path)
    for idx in design.color_change_indices:
        assert design.stitches[idx][2] == "COLOR_CHANGE"
    assert len(design.color_change_indices) == design.metadata["color_change_count"]


@pytest.mark.parametrize("dst_path", DST_FILES, ids=_ids)
def test_json_roundtrip_is_stable(dst_path: Path) -> None:
    design = dst_parser.parse(dst_path)
    once = design.to_dict()

    # dict -> JSON string -> dict is identity
    assert json.loads(json.dumps(once)) == once

    # parsing the same file twice yields the same structure
    twice = dst_parser.parse(dst_path).to_dict()
    assert twice == once
