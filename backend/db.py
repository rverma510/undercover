"""The UnderCover database: SQLite, seeded from data/."""

import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent.parent / "data"
DEFAULT_DB = Path(__file__).parent / "undercover.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    status TEXT NOT NULL,
    thread_id TEXT,
    decision TEXT,
    payout REAL,
    reasons TEXT,
    policy_section TEXT,
    decided_at TEXT,
    signed_off_by TEXT,
    signed_off_at TEXT
);
CREATE TABLE IF NOT EXISTS payments (
    claim_id TEXT PRIMARY KEY REFERENCES claims (claim_id),
    amount REAL NOT NULL,
    paid_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL REFERENCES claims (claim_id),
    thread_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS policies (policy_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers (customer_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS handlers (handler_id TEXT PRIMARY KEY, data TEXT NOT NULL);
"""

TABLES = ["steps", "payments", "claims", "policies", "customers", "handlers"]


def read_data(name: str) -> str:
    """Read one file from data/. The seed reads only the files named in seed()."""
    return (DATA / name).read_text(encoding="utf-8")


def read_json(name: str) -> Any:
    """Read one JSON file from data/."""
    return json.loads(read_data(name))


def approval_limit() -> float:
    """Return the payout above which a handler must sign off."""
    return read_json("company.json")["payout_approval_limit"]


def connect() -> sqlite3.Connection:
    """Open the database named in UNDERCOVER_DB, or backend/undercover.db."""
    conn = sqlite3.connect(
        os.getenv("UNDERCOVER_DB", str(DEFAULT_DB)), check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def get_db() -> Iterator[sqlite3.Connection]:
    """Give each request its own connection."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def seed(conn: sqlite3.Connection) -> dict[str, int]:
    """Wipe the database and load the queue and records from data/."""
    for table in TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.executescript(SCHEMA)
    records = {
        "policies": ("policy_id", read_json("policies.json")),
        "customers": ("customer_id", read_json("customers.json")),
        "handlers": ("handler_id", read_json("handlers.json")),
    }
    for table, (key, rows) in records.items():
        conn.executemany(
            f"INSERT INTO {table} VALUES (?, ?)",  # noqa: S608
            [(row[key], json.dumps(row)) for row in rows],
        )
    claims = read_json("claims.json")
    conn.executemany(
        "INSERT INTO claims (claim_id, data, status) VALUES (?, ?, 'waiting')",
        [(claim["claim_id"], json.dumps(claim)) for claim in claims],
    )
    conn.commit()
    counts = {table: len(rows) for table, (_, rows) in records.items()}
    return {"claims": len(claims), **counts}


def init(conn: sqlite3.Connection) -> None:
    """Create the tables, and seed them if the queue is empty."""
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 0:
        seed(conn)
