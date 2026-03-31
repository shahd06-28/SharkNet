# SharkNet — Database Setup

**CSIS 3750 Software Engineering | Team SharkNet**

---

## What's in this folder

- `sharknet_schema.sql` — the full SharkNet database schema (all 13 tables)
- `db_init.py` — Python script that creates the tables automatically on startup
- `README.md` — this file

---

## Requirements

- MySQL 8.x installed on your machine
- Python 3.x
- The `mysql-connector-python` package

---

## Setup Instructions

### Step 1 — Install the MySQL Python connector
```bash
pip3 install mysql-connector-python
```

### Step 2 — Create the database in MySQL
Open MySQL Workbench (or your terminal) and run:
```sql
CREATE DATABASE IF NOT EXISTS sharknet;
```

### Step 3 — Import the schema
Run this in your terminal (replace `root` with your MySQL username if different):
```bash
mysql -u root -p sharknet < sharknet_schema.sql
```
It will prompt you for your MySQL password. If you have no password, just press Enter.

### Step 4 — Update your credentials
In both `db_init.py` and `app.py`, find this block and update it with your MySQL password:
```python
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",   # <-- add your MySQL password here if you have one
    database="sharknet"
)
```

### Step 5 — Run the app
```bash
python3 app.py
```

---

## Tables

| Table | Description |
|---|---|
| USERS | Core authentication — every NSU student who signs up |
| USER_PROFILES | Extended profile info (major, bio, graduation year) |
| DEPARTMENTS | Top-level academic grouping (e.g. Computer Science) |
| SUBJECTS | Mid-level grouping under a department |
| COURSES | Individual courses with professor and semester info |
| HOMEWORK_POSTS | Student Q&A posts linked to a specific course |
| TUTOR_POSTS | Tutor availability listings linked to a specific course |
| COMMENTS | Replies on homework posts |
| VOTES | Upvotes/downvotes on posts and comments |
| BOOKMARKS | Saved posts for both post types |
| TUTOR_REVIEWS | Star ratings and written reviews on tutor listings |
| TAGS | Keyword tags (e.g. midterm, Python, Dr. Smith) |
| POST_TAGS | Junction table linking tags to homework or tutor posts |

---

## Notes

- Passwords are stored as **bcrypt hashes** — never store plaintext passwords
- NSU emails must end in `@mynsu.nova.edu` — enforced at the app level
- VOTES and BOOKMARKS are **polymorphic** — one table handles multiple post types
- `is_deleted` fields use **soft delete** — records are hidden, not removed
