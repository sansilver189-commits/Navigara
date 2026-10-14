"""SQLite database: one file in data/. Tables are created on start-up if missing."""
import sqlite3

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL,              -- 'csv', 'scrape' or 'practice'
    name        TEXT NOT NULL,
    details     TEXT,                       -- JSON: search terms, area, file name...
    status      TEXT NOT NULL DEFAULT 'done',
    found       INTEGER NOT NULL DEFAULT 0,
    checked     INTEGER NOT NULL DEFAULT 0,
    qualified   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    deleted_at  TEXT                        -- set = in "recently deleted"
);

CREATE TABLE IF NOT EXISTS leads (
    id            INTEGER PRIMARY KEY,
    batch_id      INTEGER REFERENCES batches(id),
    place_id      TEXT UNIQUE,              -- Google's id for the business
    name          TEXT NOT NULL,
    phone         TEXT,                     -- +15125550123 form
    category      TEXT,
    address       TEXT,
    city          TEXT,
    state         TEXT,
    website       TEXT,
    maps_url      TEXT,
    rating        REAL,
    review_count  INTEGER,
    review_facts  TEXT,                     -- JSON the scraper read, kept so we can re-score
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending / ready / skipped / dropped
    score         INTEGER,
    grade         TEXT,
    skip_reason   TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS leads_batch ON leads(batch_id);

-- One row per call result. Never updated except to mark a mistake as ignored.
CREATE TABLE IF NOT EXISTS call_events (
    id           INTEGER PRIMARY KEY,
    lead_id      INTEGER NOT NULL REFERENCES leads(id),
    result       TEXT NOT NULL,
    source       TEXT NOT NULL DEFAULT 'dialer',   -- 'dialer' = a real dial, 'manual' = bookkeeping
    from_number  TEXT,
    call_sid     TEXT,
    script_id    INTEGER,
    duration_sec INTEGER,
    note         TEXT,
    created_at   TEXT NOT NULL,
    ignored      INTEGER NOT NULL DEFAULT 0,
    ignored_at   TEXT
);
CREATE INDEX IF NOT EXISTS call_events_lead ON call_events(lead_id);
CREATE INDEX IF NOT EXISTS call_events_time ON call_events(created_at);

-- Small values you change from the dashboard (e.g. daily dial goal).
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db():
    """FastAPI dependency: one connection per request."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn, key, value) -> None:
    conn.execute(
        "INSERT INTO app_settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
