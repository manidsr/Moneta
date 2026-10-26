"""SQLite connection and schema."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uid         TEXT    NOT NULL UNIQUE,          -- id created by the phone; makes imports idempotent
    date        INTEGER NOT NULL,                 -- epoch milliseconds
    type        TEXT    NOT NULL CHECK (type IN ('income', 'expense')),
    amount      INTEGER NOT NULL CHECK (amount > 0),
    description TEXT    NOT NULL,
    cat         TEXT,                             -- NULL until categorised in the dashboard
    note        TEXT    NOT NULL DEFAULT '',
    ref         TEXT,
    bal         INTEGER,                          -- bank balance after, if the SMS reported it
    src         TEXT    NOT NULL DEFAULT 'sms',
    st          TEXT    NOT NULL DEFAULT 'review' CHECK (st IN ('ok', 'review')),
    raw         TEXT,                             -- original SMS text, never shown in the UI
    created     INTEGER NOT NULL                  -- epoch ms when imported
);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions (date);

CREATE TABLE IF NOT EXISTS sync_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at     INTEGER NOT NULL,
    rows_read  INTEGER NOT NULL,
    inserted   INTEGER NOT NULL,
    duplicates INTEGER NOT NULL,
    invalid    INTEGER NOT NULL,
    deleted    INTEGER NOT NULL,
    error      TEXT
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn
