"""SQLite database connection and schema bootstrap.

Usage
-----
    from pocs.poc4_order_workflow.src.database import open_db

    with open_db(":memory:") as db:
        ...   # db is a sqlite3.Connection with FK enforcement on

In production (FastAPI), open a single connection per request (or use a
thread-local connection pool).  When migrating to PostgreSQL, replace
this module with a psycopg2 / asyncpg connection factory — the SQL in
crud.py uses only standard SQL dialect.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from pocs.poc4_order_workflow.src.schema import ALL_DDL


def _configure(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row


def create_tables(conn: sqlite3.Connection) -> None:
    for ddl in ALL_DDL:
        conn.execute(ddl)
    conn.commit()


def open_connection(path: str | Path = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    _configure(conn)
    create_tables(conn)
    return conn


@contextmanager
def open_db(path: str | Path = ":memory:") -> Generator[sqlite3.Connection, None, None]:
    conn = open_connection(path)
    try:
        yield conn
    finally:
        conn.close()
