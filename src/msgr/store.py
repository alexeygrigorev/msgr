"""Local SQLite archive for pulled messages."""

import datetime
import os
import sqlite3

DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".msgr", "messages.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    android_id INTEGER NOT NULL,
    device     TEXT NOT NULL DEFAULT '',
    address    TEXT,
    date_ms    INTEGER,
    body       TEXT,
    state      TEXT NOT NULL DEFAULT 'new',
    fetched_at TEXT,
    read_at    TEXT,
    PRIMARY KEY (device, android_id)
)
"""


def db_path(explicit=None):
    return explicit or os.environ.get("MSGR_DB", DEFAULT_DB)


def connect(explicit=None):
    path = db_path(explicit)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute(SCHEMA)
    con.commit()
    return con


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def fmt_ts(date_ms):
    if not date_ms:
        return "?"
    dt = datetime.datetime.fromtimestamp(date_ms / 1000).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")


def upsert(con, device, messages):
    """Insert messages not yet in the archive; returns how many were new."""
    new = 0
    for m in messages:
        cur = con.execute(
            "SELECT 1 FROM messages WHERE device=? AND android_id=?",
            (device, m["id"]),
        )
        if cur.fetchone():
            continue
        con.execute(
            "INSERT INTO messages (android_id, device, address, date_ms, body,"
            " state, fetched_at) VALUES (?, ?, ?, ?, ?, 'new', ?)",
            (m["id"], device, m["address"], m["date_ms"], m["body"], _now()),
        )
        new += 1
    con.commit()
    return new


def list_messages(con, state):
    return con.execute(
        "SELECT * FROM messages WHERE state=? ORDER BY date_ms, android_id",
        (state,),
    ).fetchall()


def get_message(con, mid):
    return con.execute(
        "SELECT * FROM messages WHERE android_id=? ORDER BY state='new' DESC,"
        " date_ms LIMIT 1",
        (mid,),
    ).fetchone()


def mark_read(con, row):
    con.execute(
        "UPDATE messages SET state='archived', read_at=? WHERE device=? AND"
        " android_id=?",
        (_now(), row["device"], row["android_id"]),
    )
    con.commit()


def set_state(con, mid, state):
    con.execute(
        "UPDATE messages SET state=?, read_at=NULL WHERE android_id=?", (state, mid)
    )
    con.commit()
