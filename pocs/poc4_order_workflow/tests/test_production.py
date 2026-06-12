"""Tests for production-batch query."""

from __future__ import annotations

from pocs.poc4_order_workflow.src import crud
from pocs.poc4_order_workflow.src.models import (
    ColorUp,
    Customer,
    Logo,
    Order,
    OrderLineItem,
)
from pocs.poc4_order_workflow.src.production import ProductionBatch, get_production_batches
from pocs.poc4_order_workflow.src.state_machine import Status

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_THREAD_SEQ_A = [
    {"stop": 1, "needle": 1, "thread_code": "1000", "thread_name": "Black", "brand": "Madeira"},
    {"stop": 2, "needle": 2, "thread_code": "1070", "thread_name": "Gold", "brand": "Madeira"},
]
_THREAD_SEQ_B = [
    {"stop": 1, "needle": 3, "thread_code": "1001", "thread_name": "White", "brand": "Madeira"},
]


def _make_approved_cu(db, logo, style, color, thread_seq=_THREAD_SEQ_A):
    cu = ColorUp(
        logo_id=logo.logo_id,
        style_number=style,
        color_code=color,
        thread_sequence=thread_seq,
        status="Approved",
        approved_at="2026-01-01T12:00:00",
    )
    return crud.create_color_up(db, cu)


def _make_ready_line_item(db, order, logo, cu, placement="Left Chest", **kwargs):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number=cu.style_number,
            color_code=cu.color_code,
            placement=placement,
            logo_id=logo.logo_id,
            colorup_id=cu.colorup_id,
            status=Status.PRODUCTION_READY.value,
            size_quantities=kwargs.get("size_quantities", {"M": 10}),
        ),
    )
    return li


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_empty_batches_when_no_ready_items(db, customer, logo):
    batches = get_production_batches(db)
    assert batches == []


def test_single_batch(db, customer, logo, order):
    cu = _make_approved_cu(db, logo, "14728-BLK", "BLK")
    _make_ready_line_item(db, order, logo, cu)

    batches = get_production_batches(db)
    assert len(batches) == 1
    b = batches[0]
    assert isinstance(b, ProductionBatch)
    assert b.logo_id == logo.logo_id
    assert b.placement == "Left Chest"
    assert len(b.line_items) == 1


def test_same_logo_same_placement_same_thread_seq_groups_together(db, customer, logo, order):
    cu = _make_approved_cu(db, logo, "14728-BLK", "BLK", _THREAD_SEQ_A)
    _make_ready_line_item(db, order, logo, cu, size_quantities={"S": 5, "M": 10})
    _make_ready_line_item(db, order, logo, cu, size_quantities={"L": 8})

    batches = get_production_batches(db)
    assert len(batches) == 1
    assert len(batches[0].line_items) == 2
    assert batches[0].total_units == 23


def test_different_placement_creates_separate_batches(db, customer, logo, order):
    cu = _make_approved_cu(db, logo, "14728-BLK", "BLK")
    _make_ready_line_item(db, order, logo, cu, placement="Left Chest")
    _make_ready_line_item(db, order, logo, cu, placement="Cap Front")

    batches = get_production_batches(db)
    assert len(batches) == 2
    placements = {b.placement for b in batches}
    assert placements == {"Left Chest", "Cap Front"}


def test_different_thread_sequence_creates_separate_batches(db, customer, logo, order):
    cu_a = _make_approved_cu(db, logo, "14728-BLK", "BLK", _THREAD_SEQ_A)
    cu_b = _make_approved_cu(db, logo, "14728-WHT", "WHT", _THREAD_SEQ_B)

    _make_ready_line_item(db, order, logo, cu_a)
    _make_ready_line_item(db, order, logo, cu_b)

    batches = get_production_batches(db)
    assert len(batches) == 2


def test_batches_never_cross_customers(db):
    c1 = crud.create_customer(db, Customer(customer_name="Customer 1"))
    c2 = crud.create_customer(db, Customer(customer_name="Customer 2"))

    lg1 = crud.create_logo(db, Logo(customer_id=c1.customer_id, logo_name="Logo C1"))
    lg2 = crud.create_logo(db, Logo(customer_id=c2.customer_id, logo_name="Logo C2"))

    o1 = crud.create_order(db, Order(customer_id=c1.customer_id, order_date="2026-06-12"))
    o2 = crud.create_order(db, Order(customer_id=c2.customer_id, order_date="2026-06-12"))

    cu1 = _make_approved_cu(db, lg1, "STYLE-BLK", "BLK", _THREAD_SEQ_A)
    cu2 = _make_approved_cu(db, lg2, "STYLE-BLK", "BLK", _THREAD_SEQ_A)

    _make_ready_line_item(db, o1, lg1, cu1)
    _make_ready_line_item(db, o2, lg2, cu2)

    batches = get_production_batches(db)
    assert len(batches) == 2
    customer_ids = {b.customer_id for b in batches}
    assert customer_ids == {c1.customer_id, c2.customer_id}


def test_filter_by_customer(db):
    c1 = crud.create_customer(db, Customer(customer_name="Customer 1"))
    c2 = crud.create_customer(db, Customer(customer_name="Customer 2"))
    lg1 = crud.create_logo(db, Logo(customer_id=c1.customer_id, logo_name="L1"))
    lg2 = crud.create_logo(db, Logo(customer_id=c2.customer_id, logo_name="L2"))
    o1 = crud.create_order(db, Order(customer_id=c1.customer_id, order_date="2026-06-12"))
    o2 = crud.create_order(db, Order(customer_id=c2.customer_id, order_date="2026-06-12"))
    cu1 = _make_approved_cu(db, lg1, "S", "C")
    cu2 = _make_approved_cu(db, lg2, "S", "C")
    _make_ready_line_item(db, o1, lg1, cu1)
    _make_ready_line_item(db, o2, lg2, cu2)

    batches = get_production_batches(db, customer_id=c1.customer_id)
    assert len(batches) == 1
    assert batches[0].customer_id == c1.customer_id


def test_non_ready_items_excluded(db, customer, logo, order):
    cu = _make_approved_cu(db, logo, "S", "C")
    # In Production — should not appear
    crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="S",
            color_code="C",
            placement="Left Chest",
            logo_id=logo.logo_id,
            colorup_id=cu.colorup_id,
            status=Status.IN_PRODUCTION.value,
        ),
    )
    batches = get_production_batches(db)
    assert batches == []


def test_draft_colorup_excluded(db, customer, logo, order):
    cu = crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="S",
            color_code="C",
            thread_sequence=[],
            status="Draft",
        ),
    )
    crud.create_line_item(
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
    batches = get_production_batches(db)
    assert batches == []


def test_batch_customer_name(db, customer, logo, order):
    cu = _make_approved_cu(db, logo, "S", "C")
    _make_ready_line_item(db, order, logo, cu)
    batches = get_production_batches(db)
    assert batches[0].customer_name == customer.customer_name


def test_thread_key_is_order_independent(db, customer, logo, order):
    """Two color-ups whose thread_sequence dicts are key-order-different
    but value-identical must land in the same batch."""
    seq_1 = [
        {"brand": "Madeira", "needle": 1, "stop": 1, "thread_code": "1000", "thread_name": "Black"}
    ]
    seq_2 = [
        {"stop": 1, "needle": 1, "thread_name": "Black", "thread_code": "1000", "brand": "Madeira"}
    ]

    cu1 = crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="S1",
            color_code="BLK",
            thread_sequence=seq_1,
            status="Approved",
            version=1,
        ),
    )
    cu2 = crud.create_color_up(
        db,
        ColorUp(
            logo_id=logo.logo_id,
            style_number="S2",
            color_code="BLK",
            thread_sequence=seq_2,
            status="Approved",
            version=1,
        ),
    )
    _make_ready_line_item(db, order, logo, cu1)
    _make_ready_line_item(db, order, logo, cu2)

    batches = get_production_batches(db)
    assert len(batches) == 1
    assert len(batches[0].line_items) == 2
