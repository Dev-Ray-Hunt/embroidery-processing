"""Tests for the state machine — transitions, validation, and audit logging."""

from __future__ import annotations

import pytest

from pocs.poc4_order_workflow.src import crud
from pocs.poc4_order_workflow.src.models import Order, OrderLineItem
from pocs.poc4_order_workflow.src.state_machine import (
    VALID_TRANSITIONS,
    InvalidTransitionError,
    Status,
    get_history,
    transition,
    validate_transition,
)

# ---------------------------------------------------------------------------
# validate_transition (pure, no DB)
# ---------------------------------------------------------------------------


def test_all_states_have_transition_entries():
    """Every Status member must have an entry in VALID_TRANSITIONS."""
    for s in Status:
        assert s in VALID_TRANSITIONS, f"Missing entry for {s}"


def test_terminal_state_has_no_outgoing():
    assert VALID_TRANSITIONS[Status.COMPLETE] == set()


def test_valid_forward_transitions():
    valid_pairs = [
        (Status.NEW, Status.AWAITING_LOGO),
        (Status.AWAITING_LOGO, Status.COLOR_UP_IN_PROGRESS),
        (Status.AWAITING_LOGO, Status.PENDING_PRODUCTION_APPROVAL),
        (Status.COLOR_UP_IN_PROGRESS, Status.INTERNAL_REVIEW),
        (Status.COLOR_UP_IN_PROGRESS, Status.NEEDS_APPROVER),
        (Status.COLOR_UP_IN_PROGRESS, Status.SENT_FOR_APPROVAL),
        (Status.INTERNAL_REVIEW, Status.SENT_FOR_APPROVAL),
        (Status.INTERNAL_REVIEW, Status.NEEDS_APPROVER),
        (Status.INTERNAL_REVIEW, Status.COLOR_UP_IN_PROGRESS),
        (Status.NEEDS_APPROVER, Status.SENT_FOR_APPROVAL),
        (Status.SENT_FOR_APPROVAL, Status.APPROVED),
        (Status.SENT_FOR_APPROVAL, Status.PHONE_CALL),
        (Status.SENT_FOR_APPROVAL, Status.REVISION_IN_PROGRESS),
        (Status.PHONE_CALL, Status.APPROVED),
        (Status.PHONE_CALL, Status.REVISION_IN_PROGRESS),
        (Status.APPROVED, Status.PENDING_PRODUCTION_APPROVAL),
        (Status.PENDING_PRODUCTION_APPROVAL, Status.PRODUCTION_READY),
        (Status.REVISION_IN_PROGRESS, Status.COLOR_UP_IN_PROGRESS),
        (Status.PRODUCTION_READY, Status.IN_PRODUCTION),
        (Status.IN_PRODUCTION, Status.COMPLETE),
    ]
    for from_s, to_s in valid_pairs:
        validate_transition(from_s, to_s)  # should not raise


def test_invalid_transitions_raise():
    invalid_pairs = [
        (Status.NEW, Status.COMPLETE),
        (Status.NEW, Status.APPROVED),
        (Status.COMPLETE, Status.NEW),
        (Status.COMPLETE, Status.IN_PRODUCTION),
        (Status.AWAITING_LOGO, Status.COMPLETE),
        (Status.APPROVED, Status.SENT_FOR_APPROVAL),
        (Status.PRODUCTION_READY, Status.NEW),
        (Status.IN_PRODUCTION, Status.NEW),
        # The production gate is mandatory: nothing skips straight to runnable.
        (Status.AWAITING_LOGO, Status.PRODUCTION_READY),
        (Status.APPROVED, Status.PRODUCTION_READY),
    ]
    for from_s, to_s in invalid_pairs:
        with pytest.raises(InvalidTransitionError):
            validate_transition(from_s, to_s)


def test_error_message_lists_allowed_states():
    with pytest.raises(InvalidTransitionError) as exc_info:
        validate_transition(Status.NEW, Status.COMPLETE)
    msg = str(exc_info.value)
    assert "Awaiting Logo" in msg
    assert "New" in msg
    assert "Complete" in msg


# ---------------------------------------------------------------------------
# transition (requires DB)
# ---------------------------------------------------------------------------


def test_transition_advances_status(db, order, line_item):
    transition(db, line_item.line_item_id, Status.AWAITING_LOGO, actor="system")
    row = crud.get_line_item(db, line_item.line_item_id)
    assert row["status"] == "Awaiting Logo"


def test_transition_writes_history(db, order, line_item):
    transition(db, line_item.line_item_id, Status.AWAITING_LOGO, actor="ops-bot")
    history = get_history(db, line_item.line_item_id)
    assert len(history) == 1
    h = history[0]
    assert h["from_status"] == "New"
    assert h["to_status"] == "Awaiting Logo"
    assert h["actor"] == "ops-bot"
    assert h["team_proxy"] == 0  # SQLite stores bool as int


def test_transition_team_proxy_flag(db, order, line_item):
    transition(
        db,
        line_item.line_item_id,
        Status.AWAITING_LOGO,
        actor="system",
        team_proxy=True,
        notes="auto-linked",
    )
    history = get_history(db, line_item.line_item_id)
    assert history[0]["team_proxy"] == 1
    assert history[0]["notes"] == "auto-linked"


def test_invalid_transition_does_not_mutate(db, order, line_item):
    with pytest.raises(InvalidTransitionError):
        transition(db, line_item.line_item_id, Status.COMPLETE, actor="bad-actor")
    # Status must be unchanged
    row = crud.get_line_item(db, line_item.line_item_id)
    assert row["status"] == "New"


def test_transition_nonexistent_item_raises(db):
    with pytest.raises(ValueError, match="not found"):
        transition(db, 99999, Status.AWAITING_LOGO, actor="x")


def test_happy_path_full_workflow(db, customer, logo, approver):
    """Walk a line item through the complete approval workflow."""
    from pocs.poc4_order_workflow.src.models import Order, OrderLineItem

    o = crud.create_order(db, Order(customer_id=customer.customer_id, order_date="2026-06-12"))
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=o.order_id,
            style_number="AB-WHT",
            color_code="WHT",
            placement="Cap Front",
        ),
    )
    lid = li.line_item_id

    steps = [
        (Status.AWAITING_LOGO, "intake"),
        (Status.COLOR_UP_IN_PROGRESS, "artist"),
        (Status.SENT_FOR_APPROVAL, "artist"),
        (Status.APPROVED, "customer"),
        (Status.PENDING_PRODUCTION_APPROVAL, "lead"),
        (Status.PRODUCTION_READY, "production"),
        (Status.IN_PRODUCTION, "operator"),
        (Status.COMPLETE, "operator"),
    ]
    for to_status, actor in steps:
        transition(db, lid, to_status, actor=actor)

    final = crud.get_line_item(db, lid)
    assert final["status"] == "Complete"

    history = get_history(db, lid)
    assert len(history) == len(steps)
    assert [h["to_status"] for h in history] == [s.value for s, _ in steps]


def test_revision_loop(db, customer, logo, approver):
    """Revision In Progress → Color-Up In Progress loops correctly."""
    o = crud.create_order(db, Order(customer_id=customer.customer_id, order_date="2026-06-12"))
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=o.order_id,
            style_number="X-NAV",
            color_code="NAV",
            placement="Right Sleeve",
        ),
    )
    lid = li.line_item_id

    for st, actor in [
        (Status.AWAITING_LOGO, "system"),
        (Status.COLOR_UP_IN_PROGRESS, "artist"),
        (Status.SENT_FOR_APPROVAL, "artist"),
        (Status.REVISION_IN_PROGRESS, "customer"),
        (Status.COLOR_UP_IN_PROGRESS, "artist"),  # second round
        (Status.SENT_FOR_APPROVAL, "artist"),
        (Status.APPROVED, "customer"),
        (Status.PENDING_PRODUCTION_APPROVAL, "lead"),
        (Status.PRODUCTION_READY, "production"),
    ]:
        transition(db, lid, st, actor=actor)

    row = crud.get_line_item(db, lid)
    assert row["status"] == "Production Ready"


def test_phone_call_path(db, customer, logo, approver):
    """5 unanswered reminders → Phone Call → Approved."""
    o = crud.create_order(db, Order(customer_id=customer.customer_id, order_date="2026-06-12"))
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=o.order_id,
            style_number="HAT-BLK",
            color_code="BLK",
            placement="Cap Front",
        ),
    )
    lid = li.line_item_id

    for st, actor in [
        (Status.AWAITING_LOGO, "system"),
        (Status.COLOR_UP_IN_PROGRESS, "artist"),
        (Status.SENT_FOR_APPROVAL, "artist"),
        (Status.PHONE_CALL, "reminder-bot"),
        (Status.APPROVED, "lead"),
        (Status.PENDING_PRODUCTION_APPROVAL, "lead"),
        (Status.PRODUCTION_READY, "production"),
    ]:
        transition(db, lid, st, actor=actor)

    assert crud.get_line_item(db, lid)["status"] == "Production Ready"
