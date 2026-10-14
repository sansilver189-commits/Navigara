"""SQLite database: one file in data/. Tables are created on start-up if missing."""
import re
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
    source_id     TEXT,                     -- e.g. Apollo contact id
    name          TEXT NOT NULL,            -- company name
    contact_name  TEXT,
    title         TEXT,
    phone         TEXT,                     -- +15125550123 form
    phone_type    TEXT,                     -- direct / mobile / company / unknown
    email         TEXT,
    linkedin      TEXT,
    industry      TEXT,
    employees     INTEGER,
    engineers     INTEGER,
    city          TEXT,
    state         TEXT,
    country       TEXT,
    website       TEXT,
    facts         TEXT,                     -- JSON of everything imported, kept so we can re-score
    status        TEXT NOT NULL DEFAULT 'low',  -- ready / low (below cut-off) / skipped
    score         INTEGER,
    grade         TEXT,
    skip_reason   TEXT,
    pitch         TEXT,                     -- ROI / Technical
    score_detail  TEXT,                     -- JSON list of what earned the points
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

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

-- Call scripts, objection answers and text-message scripts.
CREATE TABLE IF NOT EXISTS scripts (
    id            INTEGER PRIMARY KEY,
    kind          TEXT NOT NULL,             -- call / objection / sms
    name          TEXT NOT NULL,
    body          TEXT NOT NULL DEFAULT '',  -- formatted text (simple HTML)
    in_use        INTEGER NOT NULL DEFAULT 0,  -- the one call script shown during calls
    show_in_panel INTEGER NOT NULL DEFAULT 1,  -- objection answers: show under the script
    archived      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- Small values you change from the dashboard (e.g. daily dial goal).
CREATE INDEX IF NOT EXISTS leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS leads_batch ON leads(batch_id);
CREATE UNIQUE INDEX IF NOT EXISTS leads_source ON leads(source_id) WHERE source_id IS NOT NULL;

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


def _add_missing_columns(conn) -> None:
    """Older databases get new columns added; nothing is ever removed."""
    for table, create in re.findall(r"CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\n\);", SCHEMA, re.S):
        have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if not have:
            continue  # table is new; CREATE TABLE makes it complete
        for line in create.splitlines():
            m = re.match(r"\s+(\w+)\s+(TEXT|INTEGER|REAL)", line)
            if m and m.group(1) not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {m.group(1)} {m.group(2)}")


def init_db() -> None:
    conn = connect()
    try:
        _add_missing_columns(conn)  # before the indexes, which may use new columns
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
