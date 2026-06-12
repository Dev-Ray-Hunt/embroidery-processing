"""Verify that DST stub functions raise the expected error.

These tests confirm the interface contract without needing any DST files.
"""

from __future__ import annotations

import pytest

from pocs.poc4_order_workflow.src.dst_stub import (
    DSTNotAvailableError,
    open_color_up_editor,
    parse_dst,
)


def test_parse_dst_raises_not_available(tmp_path):
    fake_dst = tmp_path / "fake.dst"
    fake_dst.write_bytes(b"\x00" * 10)
    with pytest.raises(DSTNotAvailableError):
        parse_dst(fake_dst)


def test_open_editor_raises_not_available():
    with pytest.raises(DSTNotAvailableError):
        open_color_up_editor(logo_id=1)


def test_dst_not_available_is_not_implemented_error():
    """DSTNotAvailableError must be a subclass of NotImplementedError."""
    assert issubclass(DSTNotAvailableError, NotImplementedError)
