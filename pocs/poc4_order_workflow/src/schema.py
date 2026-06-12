"""SQL DDL for POC 4.

Written for SQLite but migration-ready for PostgreSQL:
- INTEGER PRIMARY KEY → SERIAL PRIMARY KEY (or BIGSERIAL)
- BOOLEAN → BOOLEAN (both support it)
- JSON → JSONB
- TIMESTAMP → TIMESTAMP WITH TIME ZONE
- DEFAULT CURRENT_TIMESTAMP → DEFAULT NOW()
- REAL → DOUBLE PRECISION
Constraints, FK references, and UNIQUE declarations are identical.
"""

from __future__ import annotations

# One DDL string per table — ordered so FK targets come before FK sources.

CUSTOMERS_DDL = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id   INTEGER PRIMARY KEY,        -- PostgreSQL: SERIAL
    customer_name TEXT    NOT NULL,
    netsuite_account_id TEXT,
    address       TEXT,
    notes         TEXT,
    internal_review_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

APPROVERS_DDL = """
CREATE TABLE IF NOT EXISTS approvers (
    approver_id  INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    name         TEXT    NOT NULL,
    email        TEXT    NOT NULL,
    phone        TEXT,
    is_primary   BOOLEAN NOT NULL DEFAULT FALSE,
    active       BOOLEAN NOT NULL DEFAULT TRUE
)
"""

LOGOS_DDL = """
CREATE TABLE IF NOT EXISTS logos (
    logo_id                  INTEGER PRIMARY KEY,
    customer_id              INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    logo_name                TEXT    NOT NULL,
    design_number            TEXT,
    netsuite_file_cabinet_id TEXT,
    -- DST parse fields (NULL until POC 1 integration is wired in)
    dst_stitch_count         INTEGER,
    dst_color_count          INTEGER,
    dst_width_mm             REAL,          -- PostgreSQL: DOUBLE PRECISION
    dst_height_mm            REAL,
    dst_stop_count           INTEGER,
    dst_trim_count           INTEGER,
    -- Optional manual / parsed production fields
    stabilizer_topping       TEXT,
    stabilizer_backing       TEXT,
    machine_runtime_seconds  INTEGER,
    placement_default        TEXT,
    notes                    TEXT,
    active                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

COLOR_UPS_DDL = """
CREATE TABLE IF NOT EXISTS color_ups (
    colorup_id            INTEGER PRIMARY KEY,
    logo_id               INTEGER NOT NULL REFERENCES logos(logo_id) ON DELETE CASCADE,
    version               INTEGER NOT NULL DEFAULT 1,
    -- Match-key components (logo_id + style_number + color_code = exact match key)
    style_number          TEXT    NOT NULL,
    color_code            TEXT    NOT NULL,
    -- Ordered stop list: [{stop, needle, thread_code, thread_name, brand}, ...]
    thread_sequence       TEXT    NOT NULL DEFAULT '[]',  -- PostgreSQL: JSONB
    -- Draft | Pending Approval | Approved | Retired
    status                TEXT    NOT NULL DEFAULT 'Draft',
    approved_by_id        INTEGER REFERENCES approvers(approver_id),
    approved_by_team_proxy BOOLEAN NOT NULL DEFAULT FALSE,
    approved_at           TIMESTAMP,
    notes                 TEXT,
    created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Immutability: each (logo, style, color, version) is unique
    UNIQUE (logo_id, style_number, color_code, version)
)
"""

ORDERS_DDL = """
CREATE TABLE IF NOT EXISTS orders (
    order_id             INTEGER PRIMARY KEY,
    customer_id          INTEGER NOT NULL REFERENCES customers(customer_id),
    netsuite_so_number   TEXT,
    customer_po          TEXT,
    priority             TEXT    NOT NULL DEFAULT 'Normal',   -- Normal | Rush
    assigned_to          TEXT,
    order_date           TEXT    NOT NULL,   -- ISO-8601 date (DATE in PostgreSQL)
    due_date             TEXT,
    -- NULL → inherit customer.internal_review_default; TRUE/FALSE → order-level override
    internal_review_override BOOLEAN,
    special_instructions TEXT,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    -- NOTE: deliberately NO status column — status lives on order_line_items
)
"""

ORDER_LINE_ITEMS_DDL = """
CREATE TABLE IF NOT EXISTS order_line_items (
    line_item_id              INTEGER PRIMARY KEY,
    order_id                  INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    style_number              TEXT    NOT NULL,
    style_name                TEXT,
    color_code                TEXT    NOT NULL,
    size_quantities           TEXT    NOT NULL DEFAULT '{}',   -- PostgreSQL: JSONB
    logo_id                   INTEGER REFERENCES logos(logo_id),
    colorup_id                INTEGER REFERENCES color_ups(colorup_id),
    placement                 TEXT    NOT NULL,
    status                    TEXT    NOT NULL DEFAULT 'New',
    -- Force approval even when an exact match exists
    send_for_approval_override BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

STATUS_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS status_history (
    history_id    INTEGER PRIMARY KEY,
    line_item_id  INTEGER NOT NULL REFERENCES order_line_items(line_item_id) ON DELETE CASCADE,
    actor         TEXT    NOT NULL,
    from_status   TEXT,
    to_status     TEXT    NOT NULL,
    team_proxy    BOOLEAN NOT NULL DEFAULT FALSE,
    notes         TEXT,
    timestamp     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

ALL_DDL: list[str] = [
    CUSTOMERS_DDL,
    APPROVERS_DDL,
    LOGOS_DDL,
    COLOR_UPS_DDL,
    ORDERS_DDL,
    ORDER_LINE_ITEMS_DDL,
    STATUS_HISTORY_DDL,
]
