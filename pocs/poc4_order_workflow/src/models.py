"""Dataclasses for all POC 4 domain entities.

All IDs are int (SQLite ROWID / PostgreSQL SERIAL). Timestamps are
stored as ISO-8601 strings so they survive JSON serialisation and
sqlite3's default text affinity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Customers & Approvers
# ---------------------------------------------------------------------------


@dataclass
class Customer:
    customer_name: str
    customer_id: int = 0
    netsuite_account_id: str | None = None
    address: str | None = None
    notes: str | None = None
    # Internal-review gate is on by default for NEW customers; order overrides per-order.
    internal_review_default: bool = False
    created_at: str = field(default_factory=_now)


@dataclass
class Approver:
    customer_id: int
    name: str
    email: str
    approver_id: int = 0
    phone: str | None = None
    is_primary: bool = False
    active: bool = True


# ---------------------------------------------------------------------------
# Logos  (design files owned by a customer)
# ---------------------------------------------------------------------------


@dataclass
class Logo:
    customer_id: int
    logo_name: str
    logo_id: int = 0
    design_number: str | None = None
    # External key used by the NetSuite file cabinet; unknown → Awaiting Logo triage
    netsuite_file_cabinet_id: str | None = None
    # DST parse fields — populated by POC 1 integration (stubbed here)
    dst_stitch_count: int | None = None
    dst_color_count: int | None = None
    dst_width_mm: float | None = None
    dst_height_mm: float | None = None
    dst_stop_count: int | None = None
    dst_trim_count: int | None = None
    # Optional manual/parsed production fields
    stabilizer_topping: str | None = None
    stabilizer_backing: str | None = None
    machine_runtime_seconds: int | None = None
    placement_default: str | None = None
    notes: str | None = None
    active: bool = True
    created_at: str = field(default_factory=_now)


# ---------------------------------------------------------------------------
# Color-Ups  (immutable versions per logo × style × color)
# ---------------------------------------------------------------------------


@dataclass
class ColorUp:
    """An immutable, versioned color configuration for a logo on a specific garment.

    Match key = (logo_id, style_number, color_code).  Each approval round
    creates a NEW version rather than mutating the existing record.
    """

    logo_id: int
    style_number: str
    color_code: str
    # thread_sequence: list of dicts — [{stop: int, needle: int, thread_code: str,
    #   thread_name: str, brand: str}, ...]
    thread_sequence: list[dict[str, Any]]
    colorup_id: int = 0
    version: int = 1
    # Draft | Pending Approval | Approved | Retired
    status: str = "Draft"
    approved_by_id: int | None = None
    approved_by_team_proxy: bool = False
    approved_at: str | None = None
    notes: str | None = None
    created_at: str = field(default_factory=_now)

    def thread_sequence_json(self) -> str:
        return json.dumps(self.thread_sequence, sort_keys=True)


# ---------------------------------------------------------------------------
# Orders  (NetSuite SO reference; NO status field — status lives on line items)
# ---------------------------------------------------------------------------


@dataclass
class Order:
    customer_id: int
    order_date: str
    order_id: int = 0
    netsuite_so_number: str | None = None
    customer_po: str | None = None
    # Normal | Rush
    priority: str = "Normal"
    assigned_to: str | None = None
    due_date: str | None = None
    # None → use customer.internal_review_default; True/False → override
    internal_review_override: bool | None = None
    special_instructions: str | None = None
    created_at: str = field(default_factory=_now)


# ---------------------------------------------------------------------------
# Order Line Items  (status lives HERE, per line)
# ---------------------------------------------------------------------------


@dataclass
class OrderLineItem:
    order_id: int
    style_number: str
    color_code: str
    placement: str
    line_item_id: int = 0
    style_name: str | None = None
    # size_quantities: {"S": 12, "M": 24, ...}
    size_quantities: dict[str, int] = field(default_factory=dict)
    logo_id: int | None = None
    colorup_id: int | None = None
    status: str = "New"
    # Force an approval round even when an exact match exists
    send_for_approval_override: bool = False
    created_at: str = field(default_factory=_now)

    @property
    def total_units(self) -> int:
        return sum(self.size_quantities.values())

    def size_quantities_json(self) -> str:
        return json.dumps(self.size_quantities)


# ---------------------------------------------------------------------------
# Status History  (immutable audit log)
# ---------------------------------------------------------------------------


@dataclass
class StatusHistory:
    line_item_id: int
    actor: str
    to_status: str
    history_id: int = 0
    from_status: str | None = None
    team_proxy: bool = False
    notes: str | None = None
    timestamp: str = field(default_factory=_now)
