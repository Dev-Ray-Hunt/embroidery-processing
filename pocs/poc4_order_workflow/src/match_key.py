"""Match-key logic and approval cascade.

Match key: (logo_id, style_number, color_code) — EXACT match only.

A color code (e.g. MAL for Malbec) is not physically consistent across
garment styles, so all three fields must match to reuse an approved color-up.

Approval cascade
----------------
When a color-up is approved, every line item that references it and is in
an approval-pending state advances to Production Ready.  The cascade also
handles the "send_for_approval_override" flag: a line item that reached
Production Ready via an exact match will still respect the production gate.
"""

from __future__ import annotations

import sqlite3

from pocs.poc4_order_workflow.src.crud import approve_color_up
from pocs.poc4_order_workflow.src.state_machine import Status, transition


def find_approved_color_up(
    conn: sqlite3.Connection,
    logo_id: int,
    style_number: str,
    color_code: str,
) -> sqlite3.Row | None:
    """Return the most recent Approved color-up for this match key, or None."""
    return conn.execute(
        """
        SELECT * FROM color_ups
        WHERE logo_id = ?
          AND style_number = ?
          AND color_code = ?
          AND status = 'Approved'
        ORDER BY version DESC
        LIMIT 1
        """,
        (logo_id, style_number, color_code),
    ).fetchone()


def find_any_color_up(
    conn: sqlite3.Connection,
    logo_id: int,
    style_number: str,
    color_code: str,
) -> sqlite3.Row | None:
    """Return the most recent color-up (any status) for this match key, or None."""
    return conn.execute(
        """
        SELECT * FROM color_ups
        WHERE logo_id = ?
          AND style_number = ?
          AND color_code = ?
        ORDER BY version DESC
        LIMIT 1
        """,
        (logo_id, style_number, color_code),
    ).fetchone()


# Status values that the cascade should advance when a color-up is approved.
_CASCADE_FROM_STATUSES = {
    Status.SENT_FOR_APPROVAL.value,
    Status.PHONE_CALL.value,
    Status.NEEDS_APPROVER.value,
}


def cascade_approval(
    conn: sqlite3.Connection,
    colorup_id: int,
    actor: str,
    *,
    approved_by_id: int | None = None,
    team_proxy: bool = False,
    approved_at: str | None = None,
    notes: str | None = None,
) -> list[int]:
    """Mark the color-up Approved and advance all qualifying line items.

    Line items that reference *colorup_id* and are in Sent for Approval,
    Phone Call, or Needs Approver are moved to Production Ready.

    Returns the list of line_item_ids that were advanced.
    """
    approve_color_up(
        conn,
        colorup_id,
        approved_by_id=approved_by_id,
        team_proxy=team_proxy,
        approved_at=approved_at,
    )

    # Find all line items referencing this color-up that need advancing.
    placeholders = ", ".join("?" * len(_CASCADE_FROM_STATUSES))
    rows = conn.execute(
        f"""
        SELECT line_item_id, status FROM order_line_items
        WHERE colorup_id = ?
          AND status IN ({placeholders})
        """,  # noqa: S608
        (colorup_id, *_CASCADE_FROM_STATUSES),
    ).fetchall()

    advanced: list[int] = []
    for row in rows:
        lid = row["line_item_id"]
        # Each item passes through Approved → Production Ready
        transition(conn, lid, Status.APPROVED, actor, notes=notes, team_proxy=team_proxy)
        transition(conn, lid, Status.PRODUCTION_READY, actor, notes="Production gate sign-off")
        advanced.append(lid)

    return advanced


def resolve_logo_for_line_item(
    conn: sqlite3.Connection,
    line_item_id: int,
    logo_id: int,
    actor: str,
    *,
    force_approval: bool = False,
) -> str:
    """Link *logo_id* to a line item and determine its next status.

    Business rules:
    1. Line item must currently be in Awaiting Logo.
    2. If an approved color-up exists for the match key AND
       send_for_approval_override is False AND force_approval is False:
       → advance to Production Ready (exact-match fast path).
    3. Otherwise → advance to Color-Up In Progress.

    Returns the resulting status string.
    """
    row = conn.execute(
        """
        SELECT li.status, li.style_number, li.color_code,
               li.send_for_approval_override
        FROM order_line_items li
        WHERE li.line_item_id = ?
        """,
        (line_item_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"Line item {line_item_id} not found")
    if row["status"] != Status.AWAITING_LOGO.value:
        raise ValueError(
            f"Line item {line_item_id} is in '{row['status']}', expected 'Awaiting Logo'"
        )

    # Link the logo
    conn.execute(
        "UPDATE order_line_items SET logo_id = ? WHERE line_item_id = ?",
        (logo_id, line_item_id),
    )
    conn.commit()

    override = bool(row["send_for_approval_override"]) or force_approval
    match = find_approved_color_up(conn, logo_id, row["style_number"], row["color_code"])

    if match and not override:
        # Exact match — link the color-up and skip to Production Ready
        conn.execute(
            "UPDATE order_line_items SET colorup_id = ? WHERE line_item_id = ?",
            (match["colorup_id"], line_item_id),
        )
        conn.commit()
        transition(conn, line_item_id, Status.PRODUCTION_READY, actor, notes="Exact match")
        return Status.PRODUCTION_READY.value
    else:
        transition(conn, line_item_id, Status.COLOR_UP_IN_PROGRESS, actor, notes="No exact match")
        return Status.COLOR_UP_IN_PROGRESS.value
