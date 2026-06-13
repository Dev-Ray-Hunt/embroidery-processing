"""Per-line-item state machine for the order workflow.

States (13, per the NEXT.md build plan and task brief):
    New, Awaiting Logo, Color-Up In Progress, Internal Review,
    Needs Approver, Sent for Approval, Phone Call, Approved,
    Revision In Progress, Pending Production Approval, Production Ready,
    In Production, Complete

Pending Production Approval is the production-side gate: a cleared line item
(whether customer-approved OR an exact-match repeat that skipped the customer)
waits here for an internal production sign-off before it is eligible to run.

Every transition is validated and logged to status_history.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from enum import Enum


class Status(str, Enum):
    NEW = "New"
    AWAITING_LOGO = "Awaiting Logo"
    COLOR_UP_IN_PROGRESS = "Color-Up In Progress"
    INTERNAL_REVIEW = "Internal Review"
    NEEDS_APPROVER = "Needs Approver"
    SENT_FOR_APPROVAL = "Sent for Approval"
    PHONE_CALL = "Phone Call"
    APPROVED = "Approved"
    REVISION_IN_PROGRESS = "Revision In Progress"
    PENDING_PRODUCTION_APPROVAL = "Pending Production Approval"
    PRODUCTION_READY = "Production Ready"
    IN_PRODUCTION = "In Production"
    COMPLETE = "Complete"


# Valid outgoing transitions per state.
# Transitions are intentionally explicit rather than inferred — this is the
# single source of truth for the workflow rules.
VALID_TRANSITIONS: dict[Status, set[Status]] = {
    Status.NEW: {Status.AWAITING_LOGO},
    Status.AWAITING_LOGO: {
        Status.COLOR_UP_IN_PROGRESS,  # no exact match found
        # exact match exists: skips CUSTOMER approval but still needs the
        # PRODUCTION approval gate before it can run
        Status.PENDING_PRODUCTION_APPROVAL,
    },
    Status.COLOR_UP_IN_PROGRESS: {
        Status.INTERNAL_REVIEW,  # internal-review gate is on
        Status.NEEDS_APPROVER,  # gate off AND no approver on file
        Status.SENT_FOR_APPROVAL,  # gate off AND approver exists
    },
    Status.INTERNAL_REVIEW: {
        Status.NEEDS_APPROVER,  # no approver on file
        Status.SENT_FOR_APPROVAL,  # approver exists
        Status.COLOR_UP_IN_PROGRESS,  # reviewer sends back for rework
    },
    Status.NEEDS_APPROVER: {
        Status.SENT_FOR_APPROVAL,  # approver has been added
    },
    Status.SENT_FOR_APPROVAL: {
        Status.APPROVED,  # customer approves
        Status.PHONE_CALL,  # 5 unanswered reminders → escalate
        Status.REVISION_IN_PROGRESS,  # customer requests changes
    },
    Status.PHONE_CALL: {
        Status.APPROVED,  # approved during/after phone call
        Status.REVISION_IN_PROGRESS,  # changes agreed on phone
    },
    Status.APPROVED: {
        Status.PENDING_PRODUCTION_APPROVAL,  # customer-approved → production gate
    },
    Status.REVISION_IN_PROGRESS: {
        Status.COLOR_UP_IN_PROGRESS,  # new immutable version started
    },
    Status.PENDING_PRODUCTION_APPROVAL: {
        Status.PRODUCTION_READY,  # production signs off → eligible to run
    },
    Status.PRODUCTION_READY: {
        Status.IN_PRODUCTION,
    },
    Status.IN_PRODUCTION: {
        Status.COMPLETE,
    },
    Status.COMPLETE: set(),  # terminal
}


class InvalidTransitionError(ValueError):
    """Raised when a requested state transition is not permitted."""

    def __init__(self, from_status: Status, to_status: Status) -> None:
        allowed = sorted(s.value for s in VALID_TRANSITIONS.get(from_status, set()))
        super().__init__(
            f"Cannot transition from '{from_status.value}' to '{to_status.value}'. "
            f"Allowed next states: {allowed}"
        )
        self.from_status = from_status
        self.to_status = to_status


def validate_transition(from_status: Status, to_status: Status) -> None:
    """Raise InvalidTransitionError if the transition is not permitted."""
    if to_status not in VALID_TRANSITIONS.get(from_status, set()):
        raise InvalidTransitionError(from_status, to_status)


def transition(
    conn: sqlite3.Connection,
    line_item_id: int,
    to_status: Status,
    actor: str,
    *,
    notes: str | None = None,
    team_proxy: bool = False,
) -> None:
    """Advance a line item to *to_status*, validating and logging the change.

    Raises
    ------
    ValueError
        If the line item does not exist.
    InvalidTransitionError
        If the requested transition is not permitted from the current state.
    """
    row = conn.execute(
        "SELECT status FROM order_line_items WHERE line_item_id = ?",
        (line_item_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Line item {line_item_id} not found")

    from_status = Status(row["status"])
    validate_transition(from_status, to_status)

    now = datetime.now(UTC).isoformat(timespec="seconds")
    conn.execute(
        "UPDATE order_line_items SET status = ? WHERE line_item_id = ?",
        (to_status.value, line_item_id),
    )
    conn.execute(
        """
        INSERT INTO status_history
            (line_item_id, actor, from_status, to_status, team_proxy, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (line_item_id, actor, from_status.value, to_status.value, team_proxy, notes, now),
    )
    conn.commit()


def bulk_transition(
    conn: sqlite3.Connection,
    line_item_ids: list[int],
    to_status: Status,
    actor: str,
    *,
    notes: str | None = None,
    team_proxy: bool = False,
) -> list[int]:
    """Transition multiple line items; skip any that are already at *to_status*
    or for which the transition is invalid.  Returns IDs of successfully
    transitioned items.
    """
    updated: list[int] = []
    for lid in line_item_ids:
        row = conn.execute(
            "SELECT status FROM order_line_items WHERE line_item_id = ?",
            (lid,),
        ).fetchone()
        if row is None:
            continue
        current = Status(row["status"])
        if current == to_status:
            continue
        try:
            validate_transition(current, to_status)
        except InvalidTransitionError:
            continue
        transition(conn, lid, to_status, actor, notes=notes, team_proxy=team_proxy)
        updated.append(lid)
    return updated


def get_history(conn: sqlite3.Connection, line_item_id: int) -> list[sqlite3.Row]:
    """Return all status_history rows for a line item, oldest first."""
    return conn.execute(
        """
        SELECT * FROM status_history
        WHERE line_item_id = ?
        ORDER BY timestamp ASC, history_id ASC
        """,
        (line_item_id,),
    ).fetchall()
