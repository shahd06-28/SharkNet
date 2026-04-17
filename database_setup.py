import sqlite3
import json
import os

DB = "sharknet.db"
JSON_FILE = "discussion_data.json"

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")
conn.row_factory = sqlite3.Row
c = conn.cursor()

# --------------------------------------------------
# CORE TABLES (existing, with new columns added)
# --------------------------------------------------

# students
c.execute("""
CREATE TABLE IF NOT EXISTS students (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
)
""")

# discussions — now includes author_display and post_visibility
c.execute("""
CREATE TABLE IF NOT EXISTS discussions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    major           TEXT NOT NULL,
    title           TEXT NOT NULL,
    author_email    TEXT NOT NULL,
    author_display  TEXT DEFAULT 'Anonymous',
    post_visibility TEXT DEFAULT 'anonymous',
    fins_up         INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
)
""")

for col, default in [("author_display", "'Anonymous'"), ("post_visibility", "'anonymous'")]:
    try:
        c.execute(f"ALTER TABLE discussions ADD COLUMN {col} TEXT DEFAULT {default}")
    except Exception:
        pass

# replies — now includes author_display and post_visibility
c.execute("""
CREATE TABLE IF NOT EXISTS replies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id   INTEGER NOT NULL,
    reply_text      TEXT NOT NULL,
    author_email    TEXT,
    author_display  TEXT DEFAULT 'Anonymous',
    post_visibility TEXT DEFAULT 'anonymous',
    fins_up         INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (discussion_id) REFERENCES discussions(id) ON DELETE CASCADE
)
""")

for col, default in [("author_display", "'Anonymous'"), ("post_visibility", "'anonymous'")]:
    try:
        c.execute(f"ALTER TABLE replies ADD COLUMN {col} TEXT DEFAULT {default}")
    except Exception:
        pass

# tutors
c.execute("""
CREATE TABLE IF NOT EXISTS tutors (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    email      TEXT,
    major      TEXT,
    year       TEXT,
    subjects   TEXT,
    bio        TEXT,
    rating     REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now'))
)
""")

# tutor_reviews — rebuilt to match app structure
c.execute("""
CREATE TABLE IF NOT EXISTS tutor_reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id        INTEGER NOT NULL,
    author_email    TEXT NOT NULL,
    author_display  TEXT DEFAULT 'Anonymous',
    post_visibility TEXT DEFAULT 'anonymous',
    review_text     TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (tutor_id) REFERENCES tutors(id) ON DELETE CASCADE
)
""")

# discussion_likes — toggle-based, one row per user per discussion
c.execute("""
CREATE TABLE IF NOT EXISTS discussion_likes (
    discussion_id INTEGER NOT NULL,
    student_email TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (discussion_id, student_email),
    FOREIGN KEY (discussion_id) REFERENCES discussions(id) ON DELETE CASCADE
)
""")

# reply_likes
c.execute("""
CREATE TABLE IF NOT EXISTS reply_likes (
    reply_id      INTEGER NOT NULL,
    student_email TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (reply_id, student_email),
    FOREIGN KEY (reply_id) REFERENCES replies(id) ON DELETE CASCADE
)
""")

# tutor_ratings — one row per user per tutor, updatable
c.execute("""
CREATE TABLE IF NOT EXISTS tutor_ratings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id      INTEGER NOT NULL,
    student_email TEXT NOT NULL,
    rating        INTEGER NOT NULL,
    created_at    TEXT DEFAULT (datetime('now')),
    UNIQUE (tutor_id, student_email),
    FOREIGN KEY (tutor_id) REFERENCES tutors(id) ON DELETE CASCADE
)
""")

# tutor_availability — slots with booked flag
c.execute("""
CREATE TABLE IF NOT EXISTS tutor_availability (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id  INTEGER NOT NULL,
    slot_text TEXT NOT NULL,
    is_booked INTEGER DEFAULT 0,
    UNIQUE (tutor_id, slot_text),
    FOREIGN KEY (tutor_id) REFERENCES tutors(id) ON DELETE CASCADE
)
""")

# tutor_bookings
c.execute("""
CREATE TABLE IF NOT EXISTS tutor_bookings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id      INTEGER NOT NULL,
    student_email TEXT NOT NULL,
    slot_text     TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now')),
    UNIQUE (tutor_id, slot_text),
    FOREIGN KEY (tutor_id) REFERENCES tutors(id) ON DELETE CASCADE
)
""")

# tutor_requests
c.execute("""
CREATE TABLE IF NOT EXISTS tutor_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    major           TEXT NOT NULL,
    year            TEXT NOT NULL,
    subjects        TEXT NOT NULL,
    phone           TEXT,
    experience      TEXT NOT NULL,
    availability    TEXT NOT NULL,
    resume_filename TEXT,
    submitted_by    TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
)
""")

conn.commit()
print("tables created/updated!")

# --------------------------------------------------
# SEED TUTORS
# --------------------------------------------------
tutors_seed = [
    ("Jane Doe",       "CS Major",          "Senior",    "Algorithms, Data Structures, Programming"),
    ("Alice Susan",    "CS Major",          "Junior",    "Web Apps, Database Management"),
    ("Michael Brown",  "Biology Major",     "Sophomore", "General Biology, Microbiology, Lab Techniques"),
    ("Emily Lee",      "Psychology Major",  "Senior",    "Research Methods, Statistics, Essay Writing"),
    ("John Smith",     "Engineering Major", "Senior",    "Mechanics, Thermodynamics"),
    ("Samantha Green", "Business Major",    "Junior",    "Finance, Marketing, Business Strategy"),
    ("David Wilson",   "Nursing Major",     "Senior",    "Anatomy, Physiology, Clinical Skills"),
]

for name, major, year, subjects in tutors_seed:
    c.execute("""
        INSERT OR IGNORE INTO tutors (name, major, year, subjects)
        VALUES (?, ?, ?, ?)
    """, (name, major, year, subjects))

conn.commit()
print("tutors seeded!")

# --------------------------------------------------
# SEED DEFAULT AVAILABILITY
# --------------------------------------------------
default_availability = {
    "Jane Doe":       ["Tuesday 1:00 PM", "Thursday 11:00 AM", "Friday 2:00 PM"],
    "Alice Susan":    ["Monday 12:00 PM", "Wednesday 4:00 PM", "Friday 10:00 AM"],
    "Michael Brown":  ["Monday 10:00 AM", "Wednesday 1:00 PM", "Thursday 3:00 PM"],
    "Emily Lee":      ["Monday 11:00 AM", "Wednesday 2:00 PM", "Thursday 4:00 PM"],
    "John Smith":     ["Monday 3:00 PM",  "Wednesday 10:00 AM", "Friday 12:00 PM"],
    "Samantha Green": ["Tuesday 11:00 AM", "Thursday 2:00 PM", "Friday 4:00 PM"],
    "David Wilson":   ["Tuesday 9:00 AM", "Thursday 1:00 PM", "Friday 3:00 PM"],
}

for name, slots in default_availability.items():
    row = conn.execute("SELECT id FROM tutors WHERE name = ?", (name,)).fetchone()
    if not row:
        continue
    tutor_id = row["id"]
    for slot in slots:
        c.execute("""
            INSERT OR IGNORE INTO tutor_availability (tutor_id, slot_text)
            VALUES (?, ?)
        """, (tutor_id, slot))

conn.commit()
print("tutor availability seeded!")

# --------------------------------------------------
# SEED DEFAULT RATINGS
# --------------------------------------------------
default_ratings = {
    "Jane Doe": 4.9, "Alice Susan": 4.7, "Michael Brown": 4.8,
    "Emily Lee": 4.9, "John Smith": 4.8, "Samantha Green": 4.7, "David Wilson": 4.8,
}

for name, avg in default_ratings.items():
    conn.execute("UPDATE tutors SET rating = ? WHERE name = ?", (avg, name))

conn.commit()
print("tutor ratings seeded!")

# --------------------------------------------------
# SEED DEFAULT REVIEWS
# --------------------------------------------------
default_reviews = {
    "Jane Doe":       ["Super clear explanations!", "Helped me debug my projects."],
    "Alice Susan":    ["Helped me understand SQL queries.", "Super friendly and patient."],
    "Michael Brown":  ["Explains concepts in a really understandable way.", "Great study tips for exams!"],
    "Emily Lee":      ["Helped me improve my research paper.", "Very knowledgeable and patient."],
    "John Smith":     ["Great explanations for complex engineering topics.", "Helped me understand lab experiments."],
    "Samantha Green": ["Explains finance concepts clearly.", "Helped me with my marketing assignment."],
    "David Wilson":   ["Very patient and thorough explanations.", "Helped me prepare for exams effectively."],
}

for name, reviews in default_reviews.items():
    row = conn.execute("SELECT id FROM tutors WHERE name = ?", (name,)).fetchone()
    if not row:
        continue
    tutor_id = row["id"]
    for text in reviews:
        c.execute("""
            INSERT OR IGNORE INTO tutor_reviews (tutor_id, author_email, author_display, post_visibility, review_text)
            VALUES (?, ?, ?, ?, ?)
        """, (tutor_id, "", "Anonymous", "anonymous", text))

conn.commit()
print("tutor reviews seeded!")

# --------------------------------------------------
# MIGRATE OLD JSON DATA
# --------------------------------------------------
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r") as f:
        data = json.load(f)

    d_count = r_count = 0

    for d in data.get("discussions_data", []):
        title        = d.get("title") or d.get("question") or ""
        major        = d.get("major", "General")
        author_email = d.get("author_email", "unknown@mynsu.nova.edu")
        author_disp  = d.get("author_display", "Anonymous")
        post_vis     = d.get("post_visibility", "anonymous")
        fins_up      = d.get("fins_up", 0)
        created_at   = d.get("created_at") or d.get("time") or "Just now"

        c.execute("INSERT OR IGNORE INTO students (email) VALUES (?)", (author_email,))
        c.execute("""
            INSERT OR IGNORE INTO discussions
            (id, major, title, author_email, author_display, post_visibility, fins_up, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (d["id"], major, title, author_email, author_disp, post_vis, fins_up, created_at))
        d_count += 1

        for email in d.get("liked_by", []):
            c.execute("INSERT OR IGNORE INTO discussion_likes (discussion_id, student_email) VALUES (?, ?)", (d["id"], email))

        for r in d.get("replies", []):
            c.execute("""
                INSERT OR IGNORE INTO replies
                (id, discussion_id, reply_text, author_email, author_display, post_visibility, fins_up, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (r["id"], d["id"], r.get("reply_text", ""), r.get("author_email", ""),
                  r.get("author_display", "Anonymous"), r.get("post_visibility", "anonymous"),
                  r.get("fins_up", 0), r.get("created_at", "Just now")))
            r_count += 1

            for email in r.get("liked_by", []):
                c.execute("INSERT OR IGNORE INTO reply_likes (reply_id, student_email) VALUES (?, ?)", (r["id"], email))

    conn.commit()
    print(f"migrated {d_count} discussions and {r_count} replies from json!")
else:
    print("no json file found, skipping migration")

# --------------------------------------------------
# SUMMARY
# --------------------------------------------------
tables = [
    "students", "discussions", "replies", "tutors",
    "tutor_reviews", "discussion_likes", "reply_likes",
    "tutor_ratings", "tutor_availability", "tutor_bookings", "tutor_requests"
]
print()
for t in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {count} rows")

conn.close()
print(f"\ndone! db saved to {DB}")
