"""SQLite connection and schema. One small connection per request."""
import os
import sqlite3

DB_PATH = os.environ.get(
    "FINANCE_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "finance.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    date           TEXT NOT NULL,                       -- YYYY-MM-DD
    time           TEXT NOT NULL,                       -- HH:MM, 24-hour
    merchant       TEXT NOT NULL,
    amount         REAL NOT NULL CHECK (amount > 0),
    category       TEXT NOT NULL,
    payment_method TEXT NOT NULL DEFAULT 'UPI',
    source         TEXT NOT NULL DEFAULT 'manual'    CHECK (source IN ('manual','csv','screenshot')),
    status         TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed','pending_confirmation')),
    note           TEXT,
    planted_label  TEXT,                                -- HIDDEN: only for evaluation, never returned by the API
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(date);
CREATE TABLE IF NOT EXISTS agent_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id        INTEGER NOT NULL,
    trace_json    TEXT NOT NULL,              -- steps, facts, evidence, contributions, explanation
    rules_fired   TEXT NOT NULL DEFAULT '[]', -- JSON list of rule ids
    probability   REAL,                       -- NULL on the quick path (no Bayesian analysis was needed)
    risk_level    TEXT,                       -- Low / Medium / High
    outcome       TEXT NOT NULL,
    user_feedback TEXT,                       -- me / not_me / NULL
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_runs_txn ON agent_runs(txn_id);
CREATE TABLE IF NOT EXISTS merchants (
    name     TEXT PRIMARY KEY COLLATE NOCASE,
    category TEXT NOT NULL
);
"""


def get_conn(path=None):
    path = path or DB_PATH
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()
