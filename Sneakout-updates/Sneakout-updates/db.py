"""SQLite layer for SneakOut.

Replaces the former C scheduler engine (c_src/scheduler.c) and the JSON
files under data/. Schema:

  users          (email PK, name, role, dept, year, section, password_hash)
  classes        (id PK, dept, year, section, day, start, end, subject, code, room, faculty, type)
                 -- default ('SEED-*' rows) plus admin-saved per-section rows
  period_marks   (email, mark_key, status, PRIMARY KEY(email, mark_key))
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "sneakout.db"

DEFAULT_KEY = "SEED"  # dept/year/section sentinel for the built-in timetable


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                email         TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                role          TEXT NOT NULL,
                dept          TEXT,
                year          TEXT,
                section       TEXT,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS classes (
                id        TEXT PRIMARY KEY,
                dept      TEXT NOT NULL,
                year      TEXT NOT NULL,
                section   TEXT NOT NULL,
                day       TEXT NOT NULL,
                start     TEXT NOT NULL,
                end       TEXT NOT NULL,
                subject   TEXT,
                code      TEXT,
                room      TEXT,
                faculty   TEXT,
                type      TEXT NOT NULL,
                position  INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_classes_key_day
                ON classes(dept, year, section, day, position);

            CREATE TABLE IF NOT EXISTS period_marks (
                email     TEXT NOT NULL,
                mark_key  TEXT NOT NULL,
                status    TEXT NOT NULL,
                PRIMARY KEY (email, mark_key)
            );
        """)
        _seed_default_timetable(conn)
        _seed_default_admin(conn)


_ADMIN_SEED = {
    "email":         "hemanya2510408@ssn.edu.in",
    "name":          "Hemanya D",
    "role":          "admin",
    "dept":          "IT",
    "year":          "2",
    "section":       "A",
    "password_hash": "scrypt:32768:8:1$3H8pc6scg0xpbnLE$6a3aa0a2ca56977a8b61c5acbab131dfdacc60c67e8b80e45c747bd6c77be213e93b300d48ddf263c818c5c7e9310137e8bfbfe706b8a63c82fe1a6760c069bf",
}


def _seed_default_admin(conn: sqlite3.Connection):
    row = conn.execute(
        "SELECT 1 FROM users WHERE email = ?", (_ADMIN_SEED["email"],)
    ).fetchone()
    if row:
        return
    conn.execute(
        """INSERT INTO users (email, name, role, dept, year, section, password_hash)
           VALUES (:email, :name, :role, :dept, :year, :section, :password_hash)""",
        _ADMIN_SEED,
    )


# ---------------------------------------------------------------------------
# Default timetable — ported verbatim from the former C seed() in scheduler.c
# ---------------------------------------------------------------------------
_DEFAULT_ROWS = [
    ("Mon", "08:00", "09:00", "Engineering Mathematics III", "MA301",  "A-201", "Prof. S. Mehta",   "lecture"),
    ("Mon", "09:00", "11:00", "Computer Networks Lab",       "CS303L", "Lab-3", "Prof. A. Sharma",  "lab"),
    ("Mon", "11:00", "12:00", "",                            "",       "",      "",                 "free"),
    ("Mon", "12:00", "13:00", "Data Structures",             "CS201",  "B-104", "Dr. R. Iyer",      "lecture"),
    ("Mon", "14:00", "15:00", "Operating Systems",           "CS302",  "C-301", "Dr. P. Nair",      "lecture"),

    ("Tue", "09:00", "10:00", "DBMS",                        "CS304",  "A-105", "Prof. V. Gupta",   "lecture"),
    ("Tue", "10:00", "11:00", "",                            "",       "",      "",                 "free"),
    ("Tue", "11:00", "13:00", "DSA Lab",                     "CS201L", "Lab-2", "Dr. R. Iyer",      "lab"),
    ("Tue", "14:00", "15:00", "Software Engineering",        "CS305",  "B-201", "Dr. K. Reddy",     "lecture"),

    ("Wed", "08:00", "09:00", "Engineering Mathematics III", "MA301",  "A-201", "Prof. S. Mehta",   "lecture"),
    ("Wed", "09:00", "10:00", "OS Tutorial",                 "CS302T", "A-105", "Dr. P. Nair",      "tutorial"),
    ("Wed", "10:00", "11:00", "Data Structures",             "CS201",  "B-104", "Dr. R. Iyer",      "lecture"),
    ("Wed", "11:00", "13:00", "DBMS Lab",                    "CS304L", "Lab-4", "Prof. V. Gupta",   "lab"),
    ("Wed", "14:00", "15:00", "Computer Networks",           "CS303",  "C-301", "Prof. A. Sharma",  "lecture"),
    ("Wed", "16:00", "17:00", "Software Engineering",        "CS305",  "B-201", "Dr. K. Reddy",     "lecture"),

    ("Thu", "10:00", "11:00", "DBMS Tutorial",               "CS304T", "A-105", "Prof. V. Gupta",   "tutorial"),
    ("Thu", "11:00", "13:00", "",                            "",       "",      "",                 "free"),
    ("Thu", "13:00", "14:00", "",                            "",       "",      "",                 "free"),
    ("Thu", "15:00", "16:00", "Engineering Mathematics III", "MA301",  "A-201", "Prof. S. Mehta",   "lecture"),

    ("Fri", "09:00", "10:00", "Computer Networks",           "CS303",  "C-301", "Prof. A. Sharma",  "lecture"),
    ("Fri", "10:00", "11:00", "Operating Systems",           "CS302",  "C-301", "Dr. P. Nair",      "lecture"),
    ("Fri", "11:00", "12:00", "",                            "",       "",      "",                 "free"),
    ("Fri", "13:00", "15:00", "Software Lab",                "CS305L", "Lab-1", "Dr. K. Reddy",     "lab"),
    ("Fri", "16:00", "17:00", "Data Structures",             "CS201",  "B-104", "Dr. R. Iyer",      "lecture"),

    ("Sat", "08:00", "09:00", "DS Tutorial",                 "CS201T", "A-105", "Dr. R. Iyer",      "tutorial"),
    ("Sat", "09:00", "10:00", "Engineering Mathematics III", "MA301",  "A-201", "Prof. S. Mehta",   "lecture"),
]


def _seed_default_timetable(conn: sqlite3.Connection):
    row = conn.execute(
        "SELECT 1 FROM classes WHERE dept = ? LIMIT 1", (DEFAULT_KEY,)
    ).fetchone()
    if row:
        return

    per_day_pos = {}
    rows = []
    for day, start, end, subject, code, room, faculty, kind in _DEFAULT_ROWS:
        pos = per_day_pos.get(day, 0)
        per_day_pos[day] = pos + 1
        rows.append((
            f"{DEFAULT_KEY}-{day}-{pos}",
            DEFAULT_KEY, DEFAULT_KEY, DEFAULT_KEY,
            day, start, end, subject, code, room, faculty, kind, pos,
        ))
    conn.executemany(
        """INSERT INTO classes
           (id, dept, year, section, day, start, end, subject, code, room, faculty, type, position)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------
def _row_to_entry(r: sqlite3.Row) -> dict:
    return {
        "id":        r["id"],
        "startTime": r["start"],
        "endTime":   r["end"],
        "subject":   r["subject"] or "",
        "code":      r["code"] or "",
        "room":      r["room"] or "",
        "faculty":   r["faculty"] or "",
        "type":      r["type"],
        "isCurrent": False,
    }


def get_timeline(dept: str, year: str, section: str, day: str) -> list[dict]:
    """Return the timeline for (dept, year, section, day).

    Falls back to the default SEED timetable if the section has no rows for
    that day.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM classes
               WHERE dept = ? AND year = ? AND section = ? AND day = ?
               ORDER BY position""",
            (dept, year, section, day),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                """SELECT * FROM classes
                   WHERE dept = ? AND year = ? AND section = ? AND day = ?
                   ORDER BY position""",
                (DEFAULT_KEY, DEFAULT_KEY, DEFAULT_KEY, day),
            ).fetchall()
    return [_row_to_entry(r) for r in rows]


def get_week_summary() -> dict:
    """Aggregate counts across the default week. Matches the old C `week` cmd."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    per_day = []
    total_classes = total_free = total_labs = 0
    unique_codes = set()

    with get_conn() as conn:
        for d in days:
            rows = conn.execute(
                """SELECT type, code FROM classes
                   WHERE dept = ? AND day = ? ORDER BY position""",
                (DEFAULT_KEY, d),
            ).fetchall()
            c = sum(1 for r in rows if r["type"] != "free")
            f = sum(1 for r in rows if r["type"] == "free")
            l = sum(1 for r in rows if r["type"] == "lab")
            total_classes += c
            total_free += f
            total_labs += l
            for r in rows:
                if r["type"] != "free" and r["code"]:
                    unique_codes.add(r["code"])
            per_day.append({"day": d, "classCount": c, "freeCount": f, "labCount": l})

    return {
        "days": per_day,
        "totalClasses": total_classes,
        "totalFree": total_free,
        "totalLabs": total_labs,
        "uniqueSubjects": len(unique_codes),
    }


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
def get_user(email: str):
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(r) if r else None


def email_exists(email: str) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM users WHERE email = ?", (email.lower(),)
        ).fetchone() is not None


def create_user(email, name, role, dept, year, section, password_hash):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users (email, name, role, dept, year, section, password_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (email, name, role, dept, year, section, password_hash),
        )


# ---------------------------------------------------------------------------
# Admin timetable
# ---------------------------------------------------------------------------
def save_timetable(dept: str, year: str, section: str, day: str, slots: list[dict]):
    """Replace all rows for (dept, year, section, day) with `slots`."""
    with get_conn() as conn:
        conn.execute(
            """DELETE FROM classes
               WHERE dept = ? AND year = ? AND section = ? AND day = ?""",
            (dept, year, section, day),
        )
        rows = []
        for i, s in enumerate(slots):
            rows.append((
                f"{dept}-{year}-{section}-{day}-{i}",
                dept, year, section, day,
                s.get("startTime", ""), s.get("endTime", ""),
                s.get("subject", ""), s.get("code", ""),
                s.get("room", ""), s.get("faculty", ""),
                s.get("type", "lecture"), i,
            ))
        if rows:
            conn.executemany(
                """INSERT INTO classes
                   (id, dept, year, section, day, start, end, subject, code, room, faculty, type, position)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )


def get_section_timetable(dept: str, year: str, section: str) -> dict:
    """Return {day: [slots]} only for days that have section-specific rows."""
    out: dict[str, list[dict]] = {}
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM classes
               WHERE dept = ? AND year = ? AND section = ?
               ORDER BY day, position""",
            (dept, year, section),
        ).fetchall()
    for r in rows:
        out.setdefault(r["day"], []).append(_row_to_entry(r))
    return out


def freeboard_today(day: str) -> list[dict]:
    """For each (dept, year, section) that has free slots today, return them."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM classes
               WHERE day = ? AND type = 'free' AND dept != ?
               ORDER BY dept, year, section, position""",
            (day, DEFAULT_KEY),
        ).fetchall()

    grouped: dict[tuple, list[dict]] = {}
    for r in rows:
        grouped.setdefault((r["dept"], r["year"], r["section"]), []).append(_row_to_entry(r))

    return [
        {
            "dept": dept, "year": year, "section": section,
            "key": f"{dept}-{year}-{section}",
            "freeSlots": slots,
        }
        for (dept, year, section), slots in grouped.items()
    ]


# ---------------------------------------------------------------------------
# Period marks
# ---------------------------------------------------------------------------
def get_marks_for_user(email: str) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT mark_key, status FROM period_marks WHERE email = ?", (email,)
        ).fetchall()
    return {r["mark_key"]: r["status"] for r in rows}


def set_mark(email: str, key: str, status):
    with get_conn() as conn:
        if status is None:
            conn.execute(
                "DELETE FROM period_marks WHERE email = ? AND mark_key = ?",
                (email, key),
            )
        else:
            conn.execute(
                """INSERT INTO period_marks (email, mark_key, status)
                   VALUES (?, ?, ?)
                   ON CONFLICT(email, mark_key) DO UPDATE SET status = excluded.status""",
                (email, key, status),
            )
