# SneakOut — College Timetable Webapp

## Architecture

- **SQLite database** (`db.py` + `data/sneakout.db`): single source of truth for users, the default timetable, per-section admin overrides, and per-user period marks. The DB file is created and seeded automatically on first run.

  Tables:
  - `users(email PK, name, role, dept, year, section, password_hash)`
  - `classes(id PK, dept, year, section, day, start, end, subject, code, room, faculty, type, position)` — seed rows live under the `SEED` sentinel key; admin-saved rows live under the real `dept-year-section`.
  - `period_marks(email, mark_key, status)`

- **Flask backend** (`app.py`): HTML pages and REST endpoints (`/api/today`, `/api/day/<day>`, `/api/week`, `/api/admin/timetable`, `/api/period/mark`, `/api/freeboard`). Reads/writes go directly through `db.py`.

- **Frontend** (`templates/`, `static/`): plain HTML/CSS/JS recreating the "SneakOut" dark-purple design (Onboarding, Today, Week, Settings).

## Run

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000

Default admin: `hemanya2510408@ssn.edu.in` (seeded with the password from the previous JSON build).
