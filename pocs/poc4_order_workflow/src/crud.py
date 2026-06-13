"""CRUD operations for all POC 4 entities.

Each function takes an open sqlite3.Connection and a dataclass instance,
and returns the dataclass with its auto-assigned primary key filled in.
Read functions return sqlite3.Row (dict-like) to avoid double-mapping
boilerplate; callers that need a typed object can reconstruct from it.
"""

from __future__ import annotations

import json
import sqlite3

from pocs.poc4_order_workflow.src.models import (
    Approver,
    ColorUp,
    Customer,
    Logo,
    Order,
    OrderLineItem,
    StatusHistory,
)

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


def create_customer(conn: sqlite3.Connection, c: Customer) -> Customer:
    cur = conn.execute(
        """
        INSERT INTO customers
            (customer_name, netsuite_account_id, address, notes,
             internal_review_default, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            c.customer_name,
            c.netsuite_account_id,
            c.address,
            c.notes,
            c.internal_review_default,
            c.created_at,
        ),
    )
    conn.commit()
    c.customer_id = cur.lastrowid  # type: ignore[assignment]
    return c


def get_customer(conn: sqlite3.Connection, customer_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,)).fetchone()


def list_customers(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM customers ORDER BY customer_name").fetchall()


# ---------------------------------------------------------------------------
# Approvers
# ---------------------------------------------------------------------------


def create_approver(conn: sqlite3.Connection, a: Approver) -> Approver:
    cur = conn.execute(
        """
        INSERT INTO approvers
            (customer_id, name, email, phone, is_primary, active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (a.customer_id, a.name, a.email, a.phone, a.is_primary, a.active),
    )
    conn.commit()
    a.approver_id = cur.lastrowid  # type: ignore[assignment]
    return a


def list_approvers(conn: sqlite3.Connection, customer_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM approvers WHERE customer_id = ? AND active = TRUE ORDER BY is_primary DESC",
        (customer_id,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Logos
# ---------------------------------------------------------------------------


def create_logo(conn: sqlite3.Connection, logo: Logo) -> Logo:
    cur = conn.execute(
        """
        INSERT INTO logos
            (customer_id, logo_name, design_number, netsuite_file_cabinet_id,
             dst_stitch_count, dst_color_count, dst_width_mm, dst_height_mm,
             dst_stop_count, dst_trim_count, stabilizer_topping, stabilizer_backing,
             machine_runtime_seconds, placement_default, notes, active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            logo.customer_id,
            logo.logo_name,
            logo.design_number,
            logo.netsuite_file_cabinet_id,
            logo.dst_stitch_count,
            logo.dst_color_count,
            logo.dst_width_mm,
            logo.dst_height_mm,
            logo.dst_stop_count,
            logo.dst_trim_count,
            logo.stabilizer_topping,
            logo.stabilizer_backing,
            logo.machine_runtime_seconds,
            logo.placement_default,
            logo.notes,
            logo.active,
            logo.created_at,
        ),
    )
    conn.commit()
    logo.logo_id = cur.lastrowid  # type: ignore[assignment]
    return logo


def get_logo(conn: sqlite3.Connection, logo_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM logos WHERE logo_id = ?", (logo_id,)).fetchone()


def find_logo_by_file_cabinet_id(
    conn: sqlite3.Connection, customer_id: int, netsuite_file_cabinet_id: str
) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT * FROM logos
        WHERE customer_id = ? AND netsuite_file_cabinet_id = ? AND active = TRUE
        """,
        (customer_id, netsuite_file_cabinet_id),
    ).fetchone()


def update_logo_dst_fields(conn: sqlite3.Connection, logo_id: int, **kwargs: object) -> None:
    """Update DST-derived fields on a logo (called when POC 1 parse completes)."""
    allowed = {
        "dst_stitch_count",
        "dst_color_count",
        "dst_width_mm",
        "dst_height_mm",
        "dst_stop_count",
        "dst_trim_count",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE logos SET {set_clause} WHERE logo_id = ?",  # noqa: S608
        (*fields.values(), logo_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Color-Ups
# ---------------------------------------------------------------------------


def create_color_up(conn: sqlite3.Connection, cu: ColorUp) -> ColorUp:
    cur = conn.execute(
        """
        INSERT INTO color_ups
            (logo_id, version, style_number, color_code, thread_sequence,
             status, approved_by_id, approved_by_team_proxy, approved_at,
             notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cu.logo_id,
            cu.version,
            cu.style_number,
            cu.color_code,
            cu.thread_sequence_json(),
            cu.status,
            cu.approved_by_id,
            cu.approved_by_team_proxy,
            cu.approved_at,
            cu.notes,
            cu.created_at,
        ),
    )
    conn.commit()
    cu.colorup_id = cur.lastrowid  # type: ignore[assignment]
    return cu


def get_color_up(conn: sqlite3.Connection, colorup_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM color_ups WHERE colorup_id = ?", (colorup_id,)).fetchone()


def next_version(conn: sqlite3.Connection, logo_id: int, style_number: str, color_code: str) -> int:
    """Return the next version number for this match key."""
    row = conn.execute(
        """
        SELECT MAX(version) AS max_v FROM color_ups
        WHERE logo_id = ? AND style_number = ? AND color_code = ?
        """,
        (logo_id, style_number, color_code),
    ).fetchone()
    return (row["max_v"] or 0) + 1


def approve_color_up(
    conn: sqlite3.Connection,
    colorup_id: int,
    *,
    approved_by_id: int | None = None,
    team_proxy: bool = False,
    approved_at: str | None = None,
) -> None:
    """Mark a color-up Approved; used by the cascade in match_key module."""
    from datetime import UTC, datetime

    ts = approved_at or datetime.now(UTC).isoformat(timespec="seconds")
    conn.execute(
        """
        UPDATE color_ups
        SET status = 'Approved',
            approved_by_id = ?,
            approved_by_team_proxy = ?,
            approved_at = ?
        WHERE colorup_id = ?
        """,
        (approved_by_id, team_proxy, ts, colorup_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


def create_order(conn: sqlite3.Connection, order: Order) -> Order:
    cur = conn.execute(
        """
        INSERT INTO orders
            (customer_id, netsuite_so_number, customer_po, priority,
             assigned_to, order_date, due_date, internal_review_override,
             special_instructions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order.customer_id,
            order.netsuite_so_number,
            order.customer_po,
            order.priority,
            order.assigned_to,
            order.order_date,
            order.due_date,
            order.internal_review_override,
            order.special_instructions,
            order.created_at,
        ),
    )
    conn.commit()
    order.order_id = cur.lastrowid  # type: ignore[assignment]
    return order


def get_order(conn: sqlite3.Connection, order_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()


def order_status_rollup(conn: sqlite3.Connection, order_id: int) -> dict[str, int]:
    """Return {status: count} for all line items in the order."""
    rows = conn.execute(
        """
        SELECT status, COUNT(*) AS cnt
        FROM order_line_items
        WHERE order_id = ?
        GROUP BY status
        """,
        (order_id,),
    ).fetchall()
    return {r["status"]: r["cnt"] for r in rows}


# ---------------------------------------------------------------------------
# Order Line Items
# ---------------------------------------------------------------------------


def create_line_item(conn: sqlite3.Connection, li: OrderLineItem) -> OrderLineItem:
    cur = conn.execute(
        """
        INSERT INTO order_line_items
            (order_id, style_number, style_name, color_code, size_quantities,
             logo_id, colorup_id, placement, status,
             send_for_approval_override, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            li.order_id,
            li.style_number,
            li.style_name,
            li.color_code,
            li.size_quantities_json(),
            li.logo_id,
            li.colorup_id,
            li.placement,
            li.status,
            li.send_for_approval_override,
            li.created_at,
        ),
    )
    conn.commit()
    li.line_item_id = cur.lastrowid  # type: ignore[assignment]
    return li


def get_line_item(conn: sqlite3.Connection, line_item_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM order_line_items WHERE line_item_id = ?", (line_item_id,)
    ).fetchone()


def list_line_items(conn: sqlite3.Connection, order_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM order_line_items WHERE order_id = ? ORDER BY line_item_id",
        (order_id,),
    ).fetchall()


def set_line_item_logo(conn: sqlite3.Connection, line_item_id: int, logo_id: int) -> None:
    conn.execute(
        "UPDATE order_line_items SET logo_id = ? WHERE line_item_id = ?",
        (logo_id, line_item_id),
    )
    conn.commit()


def set_line_item_colorup(conn: sqlite3.Connection, line_item_id: int, colorup_id: int) -> None:
    conn.execute(
        "UPDATE order_line_items SET colorup_id = ? WHERE line_item_id = ?",
        (colorup_id, line_item_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Status History
# ---------------------------------------------------------------------------


def create_history_entry(conn: sqlite3.Connection, h: StatusHistory) -> StatusHistory:
    cur = conn.execute(
        """
        INSERT INTO status_history
            (line_item_id, actor, from_status, to_status, team_proxy, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            h.line_item_id,
            h.actor,
            h.from_status,
            h.to_status,
            h.team_proxy,
            h.notes,
            h.timestamp,
        ),
    )
    conn.commit()
    h.history_id = cur.lastrowid  # type: ignore[assignment]
    return h


def get_history(conn: sqlite3.Connection, line_item_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM status_history
        WHERE line_item_id = ?
        ORDER BY timestamp ASC, history_id ASC
        """,
        (line_item_id,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Helper: deserialise JSON columns
# ---------------------------------------------------------------------------


def decode_size_quantities(row: sqlite3.Row) -> dict[str, int]:
    return json.loads(row["size_quantities"])


def decode_thread_sequence(row: sqlite3.Row) -> list[dict]:
    return json.loads(row["thread_sequence"])
