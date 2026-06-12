"""Production-batch query.

A Production Batch is an on-demand view (not a persisted object) that
groups Production Ready line items by the key:

    (logo_id, placement, thread_sequence_canonical)

Rules:
- Only Approved color-ups (status = 'Approved').
- Only Production Ready line items.
- NEVER crosses customers — each batch belongs to exactly one customer.

The thread_sequence_canonical key is a deterministic JSON serialisation of
the color-up's thread_sequence, so two color-ups with identical stops in
identical order (same logo, style, color) hash to the same bucket.

This module has NO DST or network dependencies and runs in the cloud.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProductionBatch:
    customer_id: int
    customer_name: str
    logo_id: int
    logo_name: str
    placement: str
    thread_sequence: list[dict[str, Any]]
    line_items: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_units(self) -> int:
        return sum(li.get("total_units", 0) for li in self.line_items)

    @property
    def colorup_ids(self) -> list[int]:
        return list({li["colorup_id"] for li in self.line_items if li.get("colorup_id")})


def _canonical_thread_key(thread_sequence_json: str) -> str:
    """Normalise the thread sequence JSON for stable grouping.

    Re-serialise with sorted keys so insertion-order differences in the
    original JSON don't produce spurious group splits.
    """
    seq = json.loads(thread_sequence_json)
    return json.dumps(seq, sort_keys=True, separators=(",", ":"))


def get_production_batches(
    conn: sqlite3.Connection,
    customer_id: int | None = None,
) -> list[ProductionBatch]:
    """Return production batches, optionally filtered to one customer.

    Each batch groups Production Ready line items that share the same
    (logo, placement, thread sequence) within a single customer.
    """
    params: list[Any] = []
    customer_filter = ""
    if customer_id is not None:
        customer_filter = "AND o.customer_id = ?"
        params.append(customer_id)

    rows = conn.execute(
        f"""
        SELECT
            li.line_item_id,
            li.order_id,
            li.style_number,
            li.style_name,
            li.color_code,
            li.size_quantities,
            li.colorup_id,
            li.placement,
            li.logo_id,
            o.customer_id,
            c.customer_name,
            lg.logo_name,
            cu.thread_sequence
        FROM order_line_items li
        JOIN orders o ON o.order_id = li.order_id
        JOIN customers c ON c.customer_id = o.customer_id
        JOIN logos lg ON lg.logo_id = li.logo_id
        JOIN color_ups cu ON cu.colorup_id = li.colorup_id
        WHERE li.status = 'Production Ready'
          AND cu.status = 'Approved'
          {customer_filter}
        ORDER BY o.customer_id, li.logo_id, li.placement
        """,  # noqa: S608
        params,
    ).fetchall()

    # Group into batches by (customer_id, logo_id, placement, thread_key)
    batches: dict[tuple, ProductionBatch] = {}
    for row in rows:
        sq_raw = row["size_quantities"]
        sq = json.loads(sq_raw) if sq_raw else {}
        total_units = sum(sq.values())

        thread_key = _canonical_thread_key(row["thread_sequence"])
        group_key = (row["customer_id"], row["logo_id"], row["placement"], thread_key)

        if group_key not in batches:
            batches[group_key] = ProductionBatch(
                customer_id=row["customer_id"],
                customer_name=row["customer_name"],
                logo_id=row["logo_id"],
                logo_name=row["logo_name"],
                placement=row["placement"],
                thread_sequence=json.loads(row["thread_sequence"]),
            )

        batches[group_key].line_items.append(
            {
                "line_item_id": row["line_item_id"],
                "order_id": row["order_id"],
                "style_number": row["style_number"],
                "style_name": row["style_name"],
                "color_code": row["color_code"],
                "size_quantities": sq,
                "total_units": total_units,
                "colorup_id": row["colorup_id"],
            }
        )

    return list(batches.values())
