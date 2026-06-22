from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

import db

# ── Config ───────────────────────────────────────────────────────────────────
ADMIN_CONTACT = "hemanya2510408@ssn.edu.in"
SSN_DOMAIN    = "ssn.edu.in"

app = Flask(__name__)
app.secret_key = "sneakout-super-secret-key-change-before-deploy-2024"

FULL_DAY_NAMES = {
    "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
    "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday",
}


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


# ── Utilities ────────────────────────────────────────────────────────────────
def today_day_code():
    idx = datetime.now().weekday()   # Mon=0 … Sun=6
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][idx]


def fmt_date():
    n = datetime.now()
    return str(n.day) + " " + n.strftime("%b")


def time_to_min(t: str) -> int:
    if not t:
        return 0
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def build_day_response(timeline: list, day: str, now: str | None = None) -> dict:
    """Compute current/next/progress + counts for a timeline list."""
    now_min = time_to_min(now) if now else -1
    current = next_item = None
    class_count = free_count = lab_count = 0
    unique_codes = set()

    for item in timeline:
        s = time_to_min(item.get("startTime", ""))
        e = time_to_min(item.get("endTime", ""))
        is_free = item.get("type") == "free"

        if is_free:
            free_count += 1
        else:
            class_count += 1
            if item.get("code"):
                unique_codes.add(item["code"])
        if item.get("type") == "lab":
            lab_count += 1

        item["isCurrent"] = (not is_free) and now_min >= 0 and s <= now_min < e
        if item["isCurrent"] and current is None:
            current = item

    for item in timeline:
        if (time_to_min(item.get("startTime", "")) > now_min
                and item.get("type") != "free"):
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
        "labCount": lab_count,
        "uniqueSubjects": len(unique_codes),
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
        user     = db.get_user(email)

        if not user or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password."
        else:
            session["user_email"]   = user["email"]
            session["user_name"]    = user["name"]
            session["user_role"]    = user["role"]
            session["user_dept"]    = user.get("dept", "") or ""
            session["user_year"]    = user.get("year", "") or ""
            session["user_section"] = user.get("section", "") or ""
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
        elif db.email_exists(email):
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
            db.create_user(
                email=email, name=name, role="user",
                dept=dept, year=year, section=section,
                password_hash=generate_password_hash(password),
            )
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

    if day == "Sun":
        data = {
            "day": "Sun", "timeline": [], "classCount": 0, "freeCount": 0,
            "labCount": 0, "uniqueSubjects": 0,
            "current": None, "next": None, "progressPercent": 0,
        }
    else:
        timeline = db.get_timeline(dept, year, section, day)
        data = build_day_response(timeline, day, now)

    data["dayFullName"] = FULL_DAY_NAMES.get(data.get("day", day), day)
    data["date"] = fmt_date()

    user_marks = db.get_marks_for_user(session["user_email"])
    date_prefix = datetime.now().strftime("%Y-%m-%d") + f"-{day}"
    for i, item in enumerate(data.get("timeline", [])):
        mk = f"{date_prefix}-{i}"
        item["userMark"] = user_marks.get(mk)
        item["markKey"]  = mk

    return jsonify(data)


@app.route("/api/day/<day>")
@login_required
def api_day(day):
    if day not in FULL_DAY_NAMES or day == "Sun":
        return jsonify({"error": "unknown day"}), 404

    dept    = session.get("user_dept", "")
    year    = session.get("user_year", "")
    section = session.get("user_section", "")

    timeline = db.get_timeline(dept, year, section, day)
    data = build_day_response(timeline, day, now=None)
    data["dayFullName"] = FULL_DAY_NAMES[day]
    data["isToday"] = day == today_day_code()
    return jsonify(data)


@app.route("/api/week")
@login_required
def api_week():
    data = db.get_week_summary()
    data["todayDay"] = today_day_code()
    return jsonify(data)


# ── Admin timetable APIs ──────────────────────────────────────────────────────
@app.route("/api/admin/timetable")
@admin_required
def api_admin_timetable_get():
    dept    = request.args.get("dept", "")
    year    = request.args.get("year", "")
    section = request.args.get("section", "").upper()
    return jsonify(db.get_section_timetable(dept, year, section))


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

    db.save_timetable(dept, year, section, day, slots)
    return jsonify({
        "ok": True,
        "key": f"{dept}-{year}-{section}",
        "day": day,
    })


# ── Period mark API ───────────────────────────────────────────────────────────
@app.route("/api/period/mark", methods=["POST"])
@login_required
def api_period_mark():
    body   = request.get_json(force=True)
    mk     = body.get("key")
    status = body.get("status")

    if not mk:
        return jsonify({"error": "Missing key"}), 400

    db.set_mark(session["user_email"], mk, status)
    return jsonify({"ok": True, "status": status})


# ── Free Board API ────────────────────────────────────────────────────────────
@app.route("/api/freeboard")
@login_required
def api_freeboard():
    day = today_day_code()
    return jsonify({
        "day": day,
        "dayFullName": FULL_DAY_NAMES.get(day, day),
        "date": fmt_date(),
        "departments": db.freeboard_today(day),
    })


# ── Startup ───────────────────────────────────────────────────────────────────
db.init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
