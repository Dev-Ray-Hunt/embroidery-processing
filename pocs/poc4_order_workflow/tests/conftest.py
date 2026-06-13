"""Shared fixtures for POC 4 tests."""

from __future__ import annotations

import pytest

from pocs.poc4_order_workflow.src import crud
from pocs.poc4_order_workflow.src.database import open_connection
from pocs.poc4_order_workflow.src.models import (
    Approver,
    ColorUp,
    Customer,
    Logo,
    Order,
    OrderLineItem,
)


@pytest.fixture()
def db():
    """In-memory SQLite connection, fully bootstrapped with schema."""
    conn = open_connection(":memory:")
    yield conn
    conn.close()


@pytest.fixture()
def customer(db):
    c = crud.create_customer(db, Customer(customer_name="Alpha Omega Winery"))
    return c


@pytest.fixture()
def approver(db, customer):
    a = crud.create_approver(
        db,
        Approver(
            customer_id=customer.customer_id,
            name="Jane Smith",
            email="jane@ao.example",
            is_primary=True,
        ),
    )
    return a


@pytest.fixture()
def logo(db, customer):
    lg = crud.create_logo(
        db,
        Logo(
            customer_id=customer.customer_id,
            logo_name="AO Main Logo",
            netsuite_file_cabinet_id="FC-1001",
        ),
    )
    return lg


@pytest.fixture()
def approved_color_up(db, logo):
    cu = ColorUp(
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
            {
                "stop": 2,
                "needle": 2,
                "thread_code": "1070",
                "thread_name": "Gold",
                "brand": "Madeira",
            },
        ],
        status="Approved",
        approved_at="2026-01-01T12:00:00",
    )
    return crud.create_color_up(db, cu)


@pytest.fixture()
def order(db, customer):
    o = crud.create_order(
        db,
        Order(
            customer_id=customer.customer_id,
            order_date="2026-06-12",
            customer_po="PO-001",
        ),
    )
    return o


@pytest.fixture()
def line_item(db, order, logo):
    li = crud.create_line_item(
        db,
        OrderLineItem(
            order_id=order.order_id,
            style_number="14728-BLK",
            color_code="BLK",
            placement="Left Chest",
            size_quantities={"S": 5, "M": 10, "L": 10, "XL": 5},
            logo_id=logo.logo_id,
        ),
    )
    return li
