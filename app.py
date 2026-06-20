import json
import subprocess
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
SCHEDULER_BIN = BASE_DIR / "bin" / "scheduler"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE       = DATA_DIR / "users.json"
OVERRIDES_FILE   = DATA_DIR / "overrides.json"
MARKS_FILE       = DATA_DIR / "period_marks.json"

# ── Config ───────────────────────────────────────────────────────────────────
ADMIN_CONTACT = "hemanya2510408@ssn.edu.in"
SSN_DOMAIN    = "ssn.edu.in"

app = Flask(__name__)
app.secret_key = "sneakout-super-secret-key-change-before-deploy-2024"

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
FULL_DAY_NAMES = {
    "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
    "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday",
}

# ── In-memory hashset for O(1) email uniqueness checks ──────────────────────
_registered_emails: set[str] = set()


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_users() -> list:
    return _load_json(USERS_FILE, {"users": []})["users"]


def save_users(users: list):
    _save_json(USERS_FILE, {"users": users})


def init_email_set():
    """Load all registered emails into the in-memory hashset at startup."""
    global _registered_emails
    _registered_emails = {u["email"].lower() for u in load_users()}


def email_taken(email: str) -> bool:
    return email.lower() in _registered_emails


def register_email(email: str):
    _registered_emails.add(email.lower())


def load_overrides() -> dict:
    return _load_json(OVERRIDES_FILE, {})


def save_overrides(data: dict):
    _save_json(OVERRIDES_FILE, data)


def load_marks() -> dict:
    return _load_json(MARKS_FILE, {})


def save_marks(data: dict):
    _save_json(MARKS_FILE, data)


# ── Auth helpers ──────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login_page"))
        if session.get("user_role") != "admin":
            return redirect(url_for("today_page"))
        return f(*args, **kwargs)
    return decorated


# ── Engine & utilities ────────────────────────────────────────────────────────
def run_engine(*args):
    """Call the compiled C scheduler binary and parse JSON output."""
    result = subprocess.run(
        [str(SCHEDULER_BIN), *args],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def today_day_code():
    idx = datetime.now().weekday()   # Mon=0 … Sun=6
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][idx]


def fmt_date():
    n = datetime.now()
    return str(n.day) + " " + n.strftime("%b")


def timetable_key(dept: str, year: str, section: str) -> str:
    return f"{dept.upper()}-{year}-{section.upper()}"


def time_to_min(t: str) -> int:
    if not t:
        return 0
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def build_today_response(timeline: list, now: str, day: str) -> dict:
    """Build /api/today-style dict from an admin-defined timeline list."""
    now_min = time_to_min(now)
    current = next_item = None
    class_count = free_count = 0

    for item in timeline:
        s = time_to_min(item.get("startTime", ""))
        e = time_to_min(item.get("endTime", ""))
        item["isCurrent"] = s <= now_min < e
        if item.get("type") == "free":
            free_count += 1
        else:
            class_count += 1
            if item["isCurrent"] and current is None:
                current = item

    for item in timeline:
        if time_to_min(item.get("startTime", "")) > now_min and item.get("type") != "free":
            next_item = item
            break

    progress_percent = 0
    if current:
        s = time_to_min(current["startTime"])
        e = time_to_min(current["endTime"])
        progress_percent = int(((now_min - s) / (e - s)) * 100) if e > s else 0

    return {
        "day": day,
        "timeline": timeline,
        "classCount": class_count,
        "freeCount": free_count,
        "current": current,
        "next": next_item,
        "progressPercent": progress_percent,
    }


# ── Page routes ───────────────────────────────────────────────────────────────
@app.route("/")
def root():
    if "user_email" not in session:
        return redirect(url_for("login_page"))
    return redirect(url_for("today_page"))


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if "user_email" in session:
        return redirect(url_for("today_page"))

    error = None
    registered = request.args.get("registered") == "1"

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        users    = load_users()
        user     = next((u for u in users if u["email"] == email), None)

        if not user or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password."
        else:
            session["user_email"]   = user["email"]
            session["user_name"]    = user["name"]
            session["user_role"]    = user["role"]
            session["user_dept"]    = user.get("dept", "")
            session["user_year"]    = user.get("year", "")
            session["user_section"] = user.get("section", "")
            return redirect(url_for("today_page"))

    return render_template("login.html", error=error, registered=registered,
                           admin_contact=ADMIN_CONTACT, ssn_domain=SSN_DOMAIN)


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if "user_email" in session:
        return redirect(url_for("today_page"))

    error = None
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")
        dept     = request.form.get("dept", "")
        year     = request.form.get("year", "")
        section  = request.form.get("section", "").upper()

        if not email.endswith(f"@{SSN_DOMAIN}"):
            error = f"Only @{SSN_DOMAIN} email addresses are allowed."
        elif email_taken(email):
            error = "An account with this email already exists."
        elif not name:
            error = "Full name is required."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif not dept or not year or not section:
            error = "Please select your department, year, and section."
        else:
            users = load_users()
            users.append({
                "email":         email,
                "name":          name,
                "role":          "user",
                "dept":          dept,
                "year":          year,
                "section":       section,
                "password_hash": generate_password_hash(password),
            })
            save_users(users)
            register_email(email)   # ← add to in-memory hashset
            return redirect(url_for("login_page") + "?registered=1")

    return render_template("register.html", error=error, ssn_domain=SSN_DOMAIN)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/today")
@login_required
def today_page():
    return render_template("today.html",
        user_name=session["user_name"],
        user_role=session["user_role"],
        user_email=session["user_email"])


@app.route("/week")
@login_required
def week_page():
    return render_template("week.html",
        user_role=session["user_role"])


@app.route("/settings")
@login_required
def settings_page():
    return render_template("settings.html",
        user_name=session["user_name"],
        user_email=session["user_email"],
        user_role=session["user_role"],
        user_dept=session.get("user_dept", ""),
        user_year=session.get("user_year", ""),
        user_section=session.get("user_section", ""),
        admin_contact=ADMIN_CONTACT)


@app.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html",
        user_name=session["user_name"],
        user_role=session["user_role"])


@app.route("/freeboard")
@login_required
def freeboard_page():
    return render_template("freeboard.html",
        user_role=session["user_role"])


# ── Data APIs ─────────────────────────────────────────────────────────────────
@app.route("/api/today")
@login_required
def api_today():
    dept    = session.get("user_dept", "")
    year    = session.get("user_year", "")
    section = session.get("user_section", "")
    day     = today_day_code()
    now     = request.args.get("time") or datetime.now().strftime("%H:%M")

    overrides = load_overrides()
    key = timetable_key(dept, year, section)

    if key in overrides and day in overrides[key]:
        data = build_today_response(overrides[key][day], now, day)
    elif day == "Sun":
        data = run_engine("day", "Mon")
        data.update({"timeline": [], "classCount": 0, "freeCount": 0,
                     "current": None, "next": None, "day": "Sun"})
    else:
        data = run_engine("today", now, day)

    data["dayFullName"] = {
        "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
        "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday",
    }.get(data.get("day", day), day)
    data["date"] = fmt_date()

    # Attach per-user period marks
    marks = load_marks()
    user_marks = marks.get(session["user_email"], {})
    date_prefix = datetime.now().strftime("%Y-%m-%d") + f"-{day}"
    for i, item in enumerate(data.get("timeline", [])):
        mk = f"{date_prefix}-{i}"
        item["userMark"] = user_marks.get(mk)
        item["markKey"]  = mk

    return jsonify(data)


@app.route("/api/day/<day>")
@login_required
def api_day(day):
    if day not in FULL_DAY_NAMES:
        return jsonify({"error": "unknown day"}), 404

    dept    = session.get("user_dept", "")
    year    = session.get("user_year", "")
    section = session.get("user_section", "")
    key     = timetable_key(dept, year, section)
    overrides = load_overrides()

    if key in overrides and day in overrides[key]:
        tl = overrides[key][day]
        data = {
            "day": day, "timeline": tl,
            "classCount": sum(1 for t in tl if t.get("type") != "free"),
            "freeCount":  sum(1 for t in tl if t.get("type") == "free"),
            "labCount":   sum(1 for t in tl if t.get("type") == "lab"),
        }
    else:
        data = run_engine("day", day)

    data["dayFullName"] = FULL_DAY_NAMES[day]
    data["isToday"] = day == today_day_code()
    return jsonify(data)


@app.route("/api/week")
@login_required
def api_week():
    data = run_engine("week")
    data["todayDay"] = today_day_code()
    return jsonify(data)


# ── Admin timetable APIs ──────────────────────────────────────────────────────
@app.route("/api/admin/timetable")
@admin_required
def api_admin_timetable_get():
    dept    = request.args.get("dept", "")
    year    = request.args.get("year", "")
    section = request.args.get("section", "")
    key = timetable_key(dept, year, section)
    return jsonify(load_overrides().get(key, {}))


@app.route("/api/admin/timetable", methods=["POST"])
@admin_required
def api_admin_timetable_save():
    body    = request.get_json(force=True)
    dept    = body.get("dept", "").strip()
    year    = body.get("year", "").strip()
    section = body.get("section", "").strip().upper()
    day     = body.get("day", "").strip()
    slots   = body.get("slots", [])

    if not dept or not year or not section or not day:
        return jsonify({"error": "Missing fields"}), 400

    key = timetable_key(dept, year, section)
    overrides = load_overrides()
    overrides.setdefault(key, {})[day] = slots
    save_overrides(overrides)
    return jsonify({"ok": True, "key": key, "day": day})


# ── Period mark API ───────────────────────────────────────────────────────────
@app.route("/api/period/mark", methods=["POST"])
@login_required
def api_period_mark():
    body   = request.get_json(force=True)
    mk     = body.get("key")          # "2024-06-20-Mon-2"
    status = body.get("status")       # "free" | "taken" | null → unmark

    if not mk:
        return jsonify({"error": "Missing key"}), 400

    marks = load_marks()
    email = session["user_email"]
    marks.setdefault(email, {})

    if status is None:
        marks[email].pop(mk, None)
    else:
        marks[email][mk] = status

    save_marks(marks)
    return jsonify({"ok": True, "status": status})


# ── Free Board API ────────────────────────────────────────────────────────────
@app.route("/api/freeboard")
@login_required
def api_freeboard():
    day = today_day_code()
    overrides = load_overrides()
    result = []

    for key, days_data in overrides.items():
        if day not in days_data:
            continue
        parts = key.split("-", 2)          # ["CSE", "2", "A"]
        if len(parts) < 3:
            continue
        dept, year, section = parts
        free_slots = [s for s in days_data[day] if s.get("type") == "free"]
        if free_slots:
            result.append({
                "dept": dept, "year": year, "section": section,
                "key": key, "freeSlots": free_slots,
            })

    return jsonify({
        "day": day,
        "dayFullName": FULL_DAY_NAMES.get(day, day),
        "date": fmt_date(),
        "departments": result,
    })


# ── Startup ───────────────────────────────────────────────────────────────────
# Load registered emails into in-memory hashset when module is imported
init_email_set()

if __name__ == "__main__":
    if not SCHEDULER_BIN.exists():
        print(
            f"⚠  Scheduler binary missing at {SCHEDULER_BIN}. "
            f"Build with: gcc -O2 -o bin/scheduler c_src/scheduler.c"
        )
    app.run(host="0.0.0.0", port=5000, debug=True)
