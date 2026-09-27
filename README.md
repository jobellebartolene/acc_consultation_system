# ACC Consultation System

A role-based medical consultation management platform built with Flask, Flask-Login,
SQLAlchemy, and SQLite. Three roles — **Super Admin**, **Medical Expert**, and
**Student** — each get a dedicated, route-protected experience.

## Features

- Secure authentication: hashed passwords (Werkzeug PBKDF2), server-side sessions,
  CSRF protection on every form, account lockout after repeated failed logins.
- Role-based access control (RBAC) enforced at the route level — every blueprint
  has a `before_request` guard that checks login + role, returning **403** for any
  authenticated user of the wrong role, and redirecting anonymous users to login.
- **Super Admin**: create/edit/disable/delete any user account, create and manage
  every consultation, assign experts and observing students, view system settings.
- **Medical Expert**: dashboard of only their assigned consultations, can update
  patient records, diagnosis, status, and add clinical notes.
- **Student**: strictly view-only access to consultations they are assigned to
  observe. No edit forms are rendered, and the underlying routes reject any
  write attempt with 403 as well (defense in depth).
- Audit log of sensitive actions (logins, lockouts, user/consultation changes).
- Clean, responsive UI in a light-orange / dirty-white medical palette, no
  frontend framework — plain HTML/CSS with a little vanilla JS (confirm dialogs).

## Project Structure

```
acc_consultation/
├── app/
│   ├── __init__.py          # application factory, blueprint registration, error handlers
│   ├── extensions.py        # db, login_manager, csrf singletons
│   ├── models.py            # User, Consultation, ClinicalNote, AuditLog (SQLAlchemy)
│   ├── decorators.py        # roles_required() RBAC decorator
│   ├── audit.py             # log_action() helper
│   ├── routes/
│   │   ├── main.py          # "/" and "/dashboard" role-based redirect
│   │   ├── auth.py          # login / logout, lockout logic
│   │   ├── admin.py         # Super Admin: users + consultations CRUD, settings
│   │   ├── expert.py        # Medical Expert: own consultations, notes, diagnosis
│   │   └── student.py       # Student: view-only observed consultations
│   ├── templates/
│   │   ├── base.html, auth/, admin/, expert/, student/, errors/
│   └── static/
│       └── css/style.css    # light-orange / dirty-white theme
├── instance/                 # SQLite DB lives here (created automatically)
├── config.py                 # Config classes (dev/production), security settings
├── run.py                    # entry point (flask run / python run.py)
├── seed.py                   # creates tables + inserts sample data for all 3 roles
├── requirements.txt
├── .env.example
└── README.md
```

## Database Schema (summary)

- **users**: id, username, email, full_name, password_hash, role
  (`super_admin` / `medical_expert` / `student`), is_active_account,
  failed_login_attempts, locked_until, last_login_at, timestamps.
- **consultations**: id, title, patient_name, patient_age, patient_gender,
  description, diagnosis, status (`open` / `in_progress` / `closed`),
  expert_id (FK → users, the assigned Medical Expert), created_by_id (FK → users),
  timestamps.
- **consultation_observers**: many-to-many join table linking consultations
  to the student users assigned to observe them.
- **clinical_notes**: id, consultation_id (FK), author_id (FK → users),
  note_type (`note` / `diagnosis`), content, created_at.
- **audit_logs**: id, user_id, username, action, details, ip_address, created_at.

## Setup & Run Instructions

### 1. Create and activate a virtual environment

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables (recommended)

```bash
cp .env.example .env
# then edit .env and set a real FLASK_SECRET_KEY
```

If you skip this step, the app auto-generates a random secret key each time it
starts — fine for a quick local demo, but it means every restart invalidates
existing sessions (everyone gets logged out). Always set `FLASK_SECRET_KEY`
yourself before any real deployment.

### 4. Initialize and seed the database

```bash
python seed.py
```

This creates `instance/acc_consultation.db`, builds all tables, and inserts
sample users and consultations for all three roles (see credentials below).
Re-running it is safe — it skips seeding if data already exists. To wipe and
reseed from scratch:

```bash
python seed.py --reset
```

### 5. Run the development server

```bash
python run.py
# or
flask --app run.py run
```

The app will be available at **http://127.0.0.1:5000**.

### 6. (Production) Run with a real WSGI server

```bash
pip install gunicorn
FLASK_ENV=production FLASK_SECRET_KEY=<your-secret> gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

Also set `SESSION_COOKIE_SECURE=True` (or use `ProductionConfig`, which sets
it automatically) and serve behind HTTPS.

## Default Login Credentials (seeded sample data)

| Role            | Username        | Password       |
|-----------------|-----------------|----------------|
| Super Admin     | `admin`         | `Admin@12345`  |
| Medical Expert  | `dr.santos`     | `Expert@12345` |
| Medical Expert  | `dr.cruz`       | `Expert@12345` |
| Student         | `student.reyes` | `Student@12345`|
| Student         | `student.tan`   | `Student@12345`|

**These are sample credentials for local evaluation only.** Change or delete
them (via the Super Admin → Users screen, or `seed.py --reset` with your own
data) before using this system with real information.

## Security Notes

- Passwords are never stored or logged in plaintext — only PBKDF2 hashes.
- Every state-changing form includes a CSRF token, validated by Flask-WTF's
  `CSRFProtect`.
- All role checks happen server-side in `before_request` guards on each
  blueprint (`app/decorators.py::roles_required`), not just by hiding UI
  elements — students physically cannot POST to expert/admin endpoints.
- Repeated failed logins (5 by default) temporarily lock the account for
  15 minutes; both values are configurable in `config.py`.
- Session cookies are `HttpOnly` and `SameSite=Lax`; set
  `SESSION_COOKIE_SECURE=True` once you're serving over HTTPS.
- This is a demo/reference implementation. Before handling real patient data,
  add HTTPS termination, stronger password policies, rate limiting at the
  network layer, proper secrets management, and a compliance review (e.g.
  HIPAA/local health-data regulations) appropriate to your jurisdiction.

## Extending the System

- Swap SQLite for PostgreSQL/MySQL by changing `DATABASE_URL` in `.env` — no
  code changes needed since everything goes through SQLAlchemy.
- Add pagination to the Users/Consultations tables once data volume grows.
- Add email notifications (e.g. Flask-Mail) when a consultation is assigned.
- Add a "Change Password" self-service page for logged-in users.
