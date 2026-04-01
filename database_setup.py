
import sqlite3
import json
import os

DB = "sharknet.db"

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")
conn.row_factory = sqlite3.Row
c = conn.cursor()

# --- students (everyone who logs in) ---
c.execute("""
CREATE TABLE IF NOT EXISTS students (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
)
""")

# --- discussions (questions posted per major) ---
c.execute("""
CREATE TABLE IF NOT EXISTS discussions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    major        TEXT NOT NULL,
    title        TEXT NOT NULL,
    author_email TEXT NOT NULL,
    fins_up      INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now'))
)
""")

# --- replies (replies to a discussion) ---
c.execute("""
CREATE TABLE IF NOT EXISTS replies (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id INTEGER NOT NULL,
    reply_text    TEXT NOT NULL,
    author_email  TEXT,
    fins_up       INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (discussion_id) REFERENCES discussions(id)
)
""")

# --- tutors (students offering to tutor) ---
c.execute("""
CREATE TABLE IF NOT EXISTS tutors (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    major      TEXT NOT NULL,
    year       TEXT,
    subjects   TEXT,
    bio        TEXT,
    rating     REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now'))
)
""")

# --- tutor reviews (1-5 stars + optional comment) ---
c.execute("""
CREATE TABLE IF NOT EXISTS tutor_reviews (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id   INTEGER NOT NULL,
    reviewer   TEXT NOT NULL,
    rating     INTEGER NOT NULL,
    comment    TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (tutor_id) REFERENCES tutors(id)
)
""")

conn.commit()
print("tables created!")

# --- pull in old json data if it exists ---
JSON_FILE = "discussion_data.json"

if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r") as f:
        data = json.load(f)

    for d in data.get("discussions_data", []):
        title  = d.get("title") or d.get("question") or ""
        major  = d.get("major", "General")
        author = d.get("author_email", "unknown@mynsu.nova.edu")
        fins   = d.get("fins_up", 0)

        c.execute("INSERT OR IGNORE INTO students (email) VALUES (?)", (author,))
        c.execute("""
            INSERT OR IGNORE INTO discussions (id, major, title, author_email, fins_up)
            VALUES (?, ?, ?, ?, ?)
        """, (d["id"], major, title, author, fins))

        for r in d.get("replies", []):
            c.execute("""
                INSERT OR IGNORE INTO replies (id, discussion_id, reply_text, author_email, fins_up)
                VALUES (?, ?, ?, ?, ?)
            """, (r["id"], d["id"], r.get("reply_text", ""), r.get("author_email", ""), r.get("fins_up", 0)))

    conn.commit()
    print("json data migrated!")
else:
    print("no json found, starting fresh")

conn.close()
print(f"done! db saved to {DB}")
