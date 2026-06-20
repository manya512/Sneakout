# SneakOut — College Timetable Webapp

## Architecture

- **C engine** (`c_src/scheduler.c`): owns all schedule data and logic using
  - a **hashmap** (separate chaining) mapping day name -> array of classes
  - a dynamic **array** per day holding the timeline entries
  - a hash **set** to count unique subjects (used for stats)
  Compiled to `bin/scheduler`. It is invoked as a subprocess by Flask and
  prints a single JSON object per call.

- **Flask backend** (`app.py`): serves the HTML pages and REST endpoints
  (`/api/today`, `/api/day/<day>`, `/api/week`) that call the C binary and
  relay its JSON straight to the frontend.

- **Frontend** (`templates/`, `static/`): plain HTML/CSS/JS recreating the
  "SneakOut" dark-purple design (Onboarding, Today, Week, Settings).

## Build & run

```bash
gcc -O2 -Wall -o bin/scheduler c_src/scheduler.c
pip install -r requirements.txt
python3 app.py
```

Then open http://localhost:5000
