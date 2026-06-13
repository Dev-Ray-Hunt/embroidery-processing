"""Tests for CRUD operations across all entities."""

from __future__ import annotations

import json

import pytest

from pocs.poc4_order_workflow.src import crud
from pocs.poc4_order_workflow.src.models import (
    Approver,
    ColorUp,
    Customer,
    Logo,
    Order,
    OrderLineItem,
)

# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------


def test_create_and_get_customer(db):
    c = crud.create_customer(db, Customer(customer_name="Test Co"))
    assert c.customer_id > 0
    row = crud.get_customer(db, c.customer_id)
    assert row["customer_name"] == "Test Co"
    assert row["internal_review_default"] == 0  # False


def test_list_customers(db):
    crud.create_customer(db, Customer(customer_name="Zebra"))
    crud.create_customer(db, Customer(customer_name="Alpha"))
    names = [r["customer_name"] for r in crud.list_customers(db)]
    assert names == ["Alpha", "Zebra"]  # ordered by name


def test_customer_internal_review_default(db):
    c = crud.create_customer(db, Customer(customer_name="Strict Co", internal_review_default=True))
    row = crud.get_customer(db, c.customer_id)
    assert row["internal_review_default"] == 1


# ---------------------------------------------------------------------------
# Approver
# ---------------------------------------------------------------------------


def test_create_approver(db, customer):
    a = crud.create_approver(
        db,
        Approver(
            customer_id=customer.customer_id,
            name="Bob",
            email="bob@example.com",
            is_primary=True,
        ),
    )
    assert a.approver_id > 0
    rows = crud.list_approvers(db, customer.customer_id)
    assert len(rows) == 1
    assert rows[0]["name"] == "Bob"


def test_list_approvers_primary_first(db, customer):
    crud.create_approver(
        db, Approver(customer_id=customer.customer_id, name="Secondary", email="s@x.com")
    )
    crud.create_approver(
        db,
        Approver(
            customer_id=customer.customer_id, name="Primary", email="p@x.com", is_primary=True
        ),
    )
    rows = crud.list_approvers(db, customer.customer_id)
    assert rows[0]["name"] == "Primary"


def test_approver_inactive_excluded(db, customer):
    crud.create_approver(
        db,
        Approver(
            customer_id=customer.customer_id,
            name="Inactive",
            email="i@x.com",
            active=False,
        ),
    )
    rows = crud.list_approvers(db, customer.customer_id)
    assert rows == []


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------


def test_create_and_get_logo(db, customer):
    lg = crud.create_logo(
        db,
        Logo(
            customer_id=customer.customer_id,
            logo_name="Test Logo",
            netsuite_file_cabinet_id="FC-999",
            dst_stitch_count=15000,
        ),
    )
    assert lg.logo_id > 0
    row = crud.get_logo(db, lg.logo_id)
    assert row["logo_name"] == "Test Logo"
    assert row["netsuite_file_cabinet_id"] == "FC-999"
    assert row["dst_stitch_count"] == 15000


def test_find_logo_by_file_cabinet_id(db, customer):
    cid = customer.customer_id
    crud.create_logo(db, Logo(customer_id=cid, logo_name="L1", netsuite_file_cabinet_id="FC-A"))
    crud.create_logo(db, Logo(customer_id=cid, logo_name="L2", netsuite_file_cabinet_id="FC-B"))

    row = crud.find_logo_by_file_cabinet_id(db, customer.customer_id, "FC-A")
    assert row["logo_name"] == "L1"

    row = crud.find_logo_by_file_cabinet_id(db, customer.customer_id, "NOPE")
    assert row is None


def test_update_logo_dst_fields(db, customer):
    lg = crud.create_logo(db, Logo(customer_id=customer.customer_id, logo_name="DST Logo"))
    crud.update_logo_dst_fields(
        db,
        lg.logo_id,
        dst_stitch_count=20000,
        dst_color_count=4,
        dst_width_mm=50.5,
    )
    row = crud.get_logo(db, lg.logo_id)
    assert row["dst_stitch_count"] == 20000
    assert row["dst_color_count"] == 4
    assert abs(row["dst_width_mm"] - 50.5) < 0.01


def test_update_logo_dst_fields_ignores_unknown(db, customer):
    lg = crud.create_logo(db, Logo(customer_id=customer.customer_id, logo_name="L"))
    # should not raise, just silently ignore unknown fields
    crud.update_logo_dst_fields(db, lg.logo_id, unknown_field="boom")
    row = crud.get_logo(db, lg.logo_id)
    assert row["logo_name"] == "L"


# ---------------------------------------------------------------------------
# Color-Up
# ---------------------------------------------------------------------------


def test_create_and_get_color_up(db, logo):
    cu = crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="14728-BLK",
            color_code="BLK",
            thread_sequence=[
                {
                    "stop": 1,
                    "needle": 1,
                    "thread_code": "1000",
                    "thread_name": "Black",
                    "brand": "Madeira",
                },
            ],
        ),
    )
    assert cu.colorup_id > 0
    row = crud.get_color_up(db, cu.colorup_id)
    assert row["style_number"] == "14728-BLK"
    assert row["status"] == "Draft"
    seq = json.loads(row["thread_sequence"])
    assert seq[0]["thread_code"] == "1000"


def test_next_version(db, logo):
    assert crud.next_version(db, logo.logo_id, "14728-BLK", "BLK") == 1
    crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="14728-BLK",
            color_code="BLK",
            thread_sequence=[],
            version=1,
        ),
    )
    assert crud.next_version(db, logo.logo_id, "14728-BLK", "BLK") == 2


def test_unique_constraint_logo_style_color_version(db, logo):
    cu1 = ColorUp(
        logo_id=logo.logo_id,
        style_number="X",
        color_code="Y",
        thread_sequence=[],
        version=1,
    )
    crud.create_color_up(db, cu1)
    cu2 = ColorUp(
        logo_id=logo.logo_id,
        style_number="X",
        color_code="Y",
        thread_sequence=[],
        version=1,
    )
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        crud.create_color_up(db, cu2)


def test_approve_color_up(db, logo, approver):
    cu = crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="14728-BLK",
            color_code="BLK",
            thread_sequence=[],
        ),
    )
    crud.approve_color_up(db, cu.colorup_id, approved_by_id=approver.approver_id)
    row = crud.get_color_up(db, cu.colorup_id)
    assert row["status"] == "Approved"
    assert row["approved_by_id"] == approver.approver_id
    assert row["approved_at"] is not None


def test_team_proxy_approval(db, logo):
    cu = crud.create_color_up(
        db,
        ColorUp(logo_id=logo.logo_id, style_number="P-WHT", color_code="WHT", thread_sequence=[]),
    )
    crud.approve_color_up(db, cu.colorup_id, team_proxy=True)
    row = crud.get_color_up(db, cu.colorup_id)
    assert row["status"] == "Approved"
    assert row["approved_by_team_proxy"] == 1
    assert row["approved_by_id"] is None


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def test_create_and_get_order(db, customer):
    o = crud.create_order(
        db,
        Order(
            customer_id=customer.customer_id,
            order_date="2026-06-12",
            netsuite_so_number="SO-12345",
            customer_po="PO-001",
        ),
    )
    assert o.order_id > 0
    row = crud.get_order(db, o.order_id)
    assert row["netsuite_so_number"] == "SO-12345"
    assert row["priority"] == "Normal"
    # Confirm there is no 'status' column on orders
    with pytest.raises((IndexError, KeyError)):
        _ = row["status"]


def test_order_has_no_status_column(db, customer):
    o = crud.create_order(db, Order(customer_id=customer.customer_id, order_date="2026-06-12"))
    row = crud.get_order(db, o.order_id)
    keys = row.keys()
    assert "status" not in keys


def test_order_status_rollup(db, customer, logo):
    o = crud.create_order(db, Order(customer_id=customer.customer_id, order_date="2026-06-12"))
    for status, n in [("New", 2), ("Awaiting Logo", 1), ("Complete", 1)]:
        for _ in range(n):
            crud.create_line_item(
                db,
                OrderLineItem(
                    order_id=o.order_id,
                    style_number="S",
                    color_code="C",
                    placement="Left Chest",
                    status=status,
                ),
            )
    rollup = crud.order_status_rollup(db, o.order_id)
    assert rollup == {"New": 2, "Awaiting Logo": 1, "Complete": 1}


# ---------------------------------------------------------------------------
# Order Line Items
# ---------------------------------------------------------------------------


def test_create_and_get_line_item(db, order, logo):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="14728-BLK",
            color_code="BLK",
            placement="Left Chest",
            size_quantities={"S": 5, "M": 10},
            logo_id=logo.logo_id,
        ),
    )
    assert li.line_item_id > 0
    row = crud.get_line_item(db, li.line_item_id)
    assert row["style_number"] == "14728-BLK"
    assert row["status"] == "New"
    sq = json.loads(row["size_quantities"])
    assert sq == {"S": 5, "M": 10}


def test_line_item_total_units():
    li = OrderLineItem(
        order_id=1,
        style_number="X",
        color_code="Y",
        placement="Left Chest",
        size_quantities={"S": 2, "M": 3, "L": 5},
    )
    assert li.total_units == 10


def test_list_line_items(db, order, logo):
    for color in ["BLK", "WHT", "NAV"]:
        crud.create_line_item(
            db,
            OrderLineItem(
                order_id=order.order_id,
                style_number="X",
                color_code=color,
                placement="Left Chest",
            ),
        )
    items = crud.list_line_items(db, order.order_id)
    assert len(items) == 3


def test_set_line_item_logo(db, order, logo):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id, style_number="A", color_code="B", placement="Cap Front"
        ),
    )
    crud.set_line_item_logo(db, li.line_item_id, logo.logo_id)
    row = crud.get_line_item(db, li.line_item_id)
    assert row["logo_id"] == logo.logo_id


def test_set_line_item_colorup(db, order, logo, approved_color_up):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id, style_number="A", color_code="B", placement="Cap Front"
        ),
    )
    crud.set_line_item_colorup(db, li.line_item_id, approved_color_up.colorup_id)
    row = crud.get_line_item(db, li.line_item_id)
    assert row["colorup_id"] == approved_color_up.colorup_id


# ---------------------------------------------------------------------------
# Foreign key enforcement
# ---------------------------------------------------------------------------


def test_fk_enforcement_order_references_customer(db):
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        crud.create_order(db, Order(customer_id=99999, order_date="2026-06-12"))


def test_fk_enforcement_line_item_references_order(db):
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        crud.create_line_item(
            db,
            OrderLineItem(order_id=99999, style_number="X", color_code="Y", placement="Cap Front"),
        )
