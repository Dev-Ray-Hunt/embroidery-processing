"""Tests for match-key logic and approval cascade."""

from __future__ import annotations

import pytest

from pocs.poc4_order_workflow.src import crud
from pocs.poc4_order_workflow.src.match_key import (
    cascade_approval,
    find_approved_color_up,
    resolve_logo_for_line_item,
)
from pocs.poc4_order_workflow.src.models import (
    ColorUp,
    Order,
    OrderLineItem,
)
from pocs.poc4_order_workflow.src.state_machine import Status

# ---------------------------------------------------------------------------
# find_approved_color_up
# ---------------------------------------------------------------------------


def test_find_approved_color_up_returns_match(db, logo, approved_color_up):
    row = find_approved_color_up(db, logo.logo_id, "14728-BLK", "BLK")
    assert row is not None
    assert row["colorup_id"] == approved_color_up.colorup_id


def test_find_approved_returns_none_when_draft(db, logo):
    crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="X",
            color_code="Y",
            thread_sequence=[],
            status="Draft",
        ),
    )
    row = find_approved_color_up(db, logo.logo_id, "X", "Y")
    assert row is None


def test_find_approved_exact_match_all_three_fields(db, logo):
    crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="STYLE-A",
            color_code="BLK",
            thread_sequence=[],
            status="Approved",
        ),
    )
    # Same style, different color
    assert find_approved_color_up(db, logo.logo_id, "STYLE-A", "WHT") is None
    # Different style, same color
    assert find_approved_color_up(db, logo.logo_id, "STYLE-B", "BLK") is None
    # Exact match
    assert find_approved_color_up(db, logo.logo_id, "STYLE-A", "BLK") is not None


def test_find_approved_returns_latest_version(db, logo):
    for v in range(1, 4):
        cu = ColorUp(
            logo_id=logo.logo_id,
            style_number="P",
            color_code="Q",
            thread_sequence=[{"stop": v}],
            status="Approved",
            version=v,
        )
        crud.create_color_up(db, cu)
    row = find_approved_color_up(db, logo.logo_id, "P", "Q")
    assert row["version"] == 3


def test_color_code_not_portable_across_styles(db, logo):
    """MAL color code on style A must not match style B — key requires all three."""
    for style in ["POLO-BLK", "HAT-BLK"]:
        crud.create_color_up(
            db,
            ColorUp(
                logo_id=logo.logo_id,
                style_number=style,
                color_code="MAL",
                thread_sequence=[],
                status="Approved",
            ),
        )
    # Only exact three-part key matches
    assert find_approved_color_up(db, logo.logo_id, "POLO-BLK", "MAL") is not None
    assert find_approved_color_up(db, logo.logo_id, "HAT-BLK", "MAL") is not None
    assert find_approved_color_up(db, logo.logo_id, "VEST-BLK", "MAL") is None


# ---------------------------------------------------------------------------
# cascade_approval
# ---------------------------------------------------------------------------


def _make_pending_line_item(db, order, logo, color_up, status=Status.SENT_FOR_APPROVAL.value):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number=color_up.style_number if hasattr(color_up, "style_number") else "X",
            color_code="BLK",
            placement="Left Chest",
            logo_id=logo.logo_id,
            colorup_id=color_up.colorup_id if hasattr(color_up, "colorup_id") else None,
            status=status,
        ),
    )
    return li


def test_cascade_approval_advances_sent_for_approval(db, customer, logo, order, approver):
    cu = crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="14728-BLK",
            color_code="BLK",
            thread_sequence=[],
            status="Pending Approval",
        ),
    )

    li1 = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="14728-BLK",
            color_code="BLK",
            placement="Left Chest",
            logo_id=logo.logo_id,
            colorup_id=cu.colorup_id,
            status=Status.SENT_FOR_APPROVAL.value,
        ),
    )
    li2 = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="14728-BLK",
            color_code="BLK",
            placement="Right Sleeve",
            logo_id=logo.logo_id,
            colorup_id=cu.colorup_id,
            status=Status.SENT_FOR_APPROVAL.value,
        ),
    )

    advanced = cascade_approval(
        db, cu.colorup_id, actor="customer", approved_by_id=approver.approver_id
    )

    assert set(advanced) == {li1.line_item_id, li2.line_item_id}
    for lid in [li1.line_item_id, li2.line_item_id]:
        row = crud.get_line_item(db, lid)
        # Cascade stops at the production gate, not Production Ready.
        assert row["status"] == "Pending Production Approval"

    cu_row = crud.get_color_up(db, cu.colorup_id)
    assert cu_row["status"] == "Approved"


def test_cascade_approval_phone_call_items(db, customer, logo, order, approver):
    cu = crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="S",
            color_code="C",
            thread_sequence=[],
            status="Pending Approval",
        ),
    )
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="S",
            color_code="C",
            placement="Left Chest",
            logo_id=logo.logo_id,
            colorup_id=cu.colorup_id,
            status=Status.PHONE_CALL.value,
        ),
    )
    advanced = cascade_approval(db, cu.colorup_id, actor="lead", team_proxy=True)
    assert li.line_item_id in advanced
    row = crud.get_line_item(db, li.line_item_id)
    assert row["status"] == "Pending Production Approval"


def test_cascade_skips_already_advanced_items(db, customer, logo, order):
    cu = crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="S",
            color_code="C",
            thread_sequence=[],
            status="Pending Approval",
        ),
    )
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="S",
            color_code="C",
            placement="Left Chest",
            logo_id=logo.logo_id,
            colorup_id=cu.colorup_id,
            status=Status.PRODUCTION_READY.value,
        ),
    )
    advanced = cascade_approval(db, cu.colorup_id, actor="system")
    # Already at Production Ready — not in the returned list
    assert li.line_item_id not in advanced
    # Status unchanged
    assert crud.get_line_item(db, li.line_item_id)["status"] == "Production Ready"


def test_cascade_leaves_needs_approver_untouched(db, customer, logo, order):
    """A Needs Approver line was never sent — the cascade must skip it, not crash.

    Regression for the bug where Needs Approver was in the cascade set but the
    state machine forbids Needs Approver -> Approved.
    """
    cu = crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="S",
            color_code="C",
            thread_sequence=[],
            status="Pending Approval",
        ),
    )
    sent = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="S",
            color_code="C",
            placement="Left Chest",
            logo_id=logo.logo_id,
            colorup_id=cu.colorup_id,
            status=Status.SENT_FOR_APPROVAL.value,
        ),
    )
    needs_approver = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="S",
            color_code="C",
            placement="Right Sleeve",
            logo_id=logo.logo_id,
            colorup_id=cu.colorup_id,
            status=Status.NEEDS_APPROVER.value,
        ),
    )

    advanced = cascade_approval(db, cu.colorup_id, actor="customer")

    # Sent item advances to the production gate; Needs Approver item is untouched.
    assert advanced == [sent.line_item_id]
    assert crud.get_line_item(db, sent.line_item_id)["status"] == "Pending Production Approval"
    assert crud.get_line_item(db, needs_approver.line_item_id)["status"] == "Needs Approver"


def test_production_approve_clears_the_gate(db, order, logo, approved_color_up):
    """production_approve advances Pending Production Approval -> Production Ready."""
    from pocs.poc4_order_workflow.src.production import production_approve

    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="14728-BLK",
            color_code="BLK",
            placement="Left Chest",
            status=Status.AWAITING_LOGO.value,
        ),
    )
    resolve_logo_for_line_item(db, li.line_item_id, logo.logo_id, actor="system")
    assert crud.get_line_item(db, li.line_item_id)["status"] == "Pending Production Approval"

    production_approve(db, li.line_item_id, actor="production-lead")
    assert crud.get_line_item(db, li.line_item_id)["status"] == "Production Ready"


def test_cascade_does_not_cross_customers(db):
    """Line items from different customers sharing a logo should not cascade."""
    from pocs.poc4_order_workflow.src.models import Customer, Logo

    c1 = crud.create_customer(db, Customer(customer_name="Cust A"))
    c2 = crud.create_customer(db, Customer(customer_name="Cust B"))

    lg1 = crud.create_logo(db, Logo(customer_id=c1.customer_id, logo_name="Logo A"))
    lg2 = crud.create_logo(db, Logo(customer_id=c2.customer_id, logo_name="Logo B"))

    cu1 = crud.create_color_up(
        db,
        ColorUp(logo_id=lg1.logo_id, style_number="S", color_code="C", thread_sequence=[]),
    )
    cu2 = crud.create_color_up(
        db,
        ColorUp(logo_id=lg2.logo_id, style_number="S", color_code="C", thread_sequence=[]),
    )

    o1 = crud.create_order(db, Order(customer_id=c1.customer_id, order_date="2026-06-12"))
    o2 = crud.create_order(db, Order(customer_id=c2.customer_id, order_date="2026-06-12"))

    li1 = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=o1.order_id,
            style_number="S",
            color_code="C",
            placement="Left Chest",
            logo_id=lg1.logo_id,
            colorup_id=cu1.colorup_id,
            status=Status.SENT_FOR_APPROVAL.value,
        ),
    )
    li2 = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=o2.order_id,
            style_number="S",
            color_code="C",
            placement="Left Chest",
            logo_id=lg2.logo_id,
            colorup_id=cu2.colorup_id,
            status=Status.SENT_FOR_APPROVAL.value,
        ),
    )

    # Approving cu1 should NOT advance li2
    advanced = cascade_approval(db, cu1.colorup_id, actor="system")
    assert li1.line_item_id in advanced
    assert li2.line_item_id not in advanced
    assert crud.get_line_item(db, li2.line_item_id)["status"] == Status.SENT_FOR_APPROVAL.value


# ---------------------------------------------------------------------------
# resolve_logo_for_line_item
# ---------------------------------------------------------------------------


def test_resolve_logo_exact_match_goes_to_production_gate(db, order, logo, approved_color_up):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="14728-BLK",
            color_code="BLK",
            placement="Left Chest",
            status=Status.AWAITING_LOGO.value,
        ),
    )
    result = resolve_logo_for_line_item(db, li.line_item_id, logo.logo_id, actor="system")
    # Exact match skips the customer but still lands at the production gate.
    assert result == Status.PENDING_PRODUCTION_APPROVAL.value
    row = crud.get_line_item(db, li.line_item_id)
    assert row["logo_id"] == logo.logo_id
    assert row["colorup_id"] == approved_color_up.colorup_id


def test_resolve_logo_no_match_goes_to_color_up_in_progress(db, order, logo):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="NEWSTYLE",
            color_code="WHT",
            placement="Cap Front",
            status=Status.AWAITING_LOGO.value,
        ),
    )
    result = resolve_logo_for_line_item(db, li.line_item_id, logo.logo_id, actor="artist")
    assert result == Status.COLOR_UP_IN_PROGRESS.value


def test_resolve_logo_override_forces_approval_path(db, order, logo, approved_color_up):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="14728-BLK",
            color_code="BLK",
            placement="Left Chest",
            status=Status.AWAITING_LOGO.value,
            send_for_approval_override=True,  # force approval even with exact match
        ),
    )
    result = resolve_logo_for_line_item(db, li.line_item_id, logo.logo_id, actor="artist")
    assert result == Status.COLOR_UP_IN_PROGRESS.value


def test_resolve_logo_requires_awaiting_logo_state(db, order, logo):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="X",
            color_code="Y",
            placement="Left Chest",
            status="New",  # wrong state
        ),
    )
    with pytest.raises(ValueError, match="Awaiting Logo"):
        resolve_logo_for_line_item(db, li.line_item_id, logo.logo_id, actor="x")
