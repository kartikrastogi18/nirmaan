# TotalWorks — rebuild

A ground-up rebuild of the civil construction management platform: Flask +
SQLAlchemy + SQLite backend (replacing the old JSON-file datastore and
global Python lock), a thin vanilla-JS frontend wired to the real API, and
a feedback/discussion feed open to the whole project team, Client included.

## What's in this drop

```
totalworks/
├── app/
│   ├── __init__.py          # app factory: extensions, SQLite WAL config, blueprint registration
│   ├── config.py             # Development / Testing / Production config classes
│   ├── extensions.py         # db, bcrypt, migrate, jwt singletons
│   ├── errors.py             # centralized JSON error handlers
│   ├── models/                # one file per module, no monoliths
│   │   ├── mixins.py          # TimestampMixin
│   │   ├── user.py            # User, UserRole, UserStatus
│   │   ├── project.py         # Project (the "site")
│   │   ├── access.py          # ProjectAccess — the RBAC/isolation join table
│   │   ├── task.py
│   │   ├── inventory.py       # InventoryItem, StockMovement, MaterialRequest
│   │   ├── drawing.py         # Drawing, DrawingRevision (version control)
│   │   ├── boq.py
│   │   ├── finance.py         # Expense
│   │   ├── labour.py          # LabourRecord
│   │   ├── progress.py        # ProgressLog, ProgressPhoto
│   │   ├── message.py         # Message (feedback feed), Notification
│   │   └── audit.py           # AuditLog
│   ├── services/
│   │   ├── access_control.py  # RBAC (roles_required) + site isolation (project_access_required)
│   │   └── calculators.py     # civil engineering toolkit — pure functions, unit tested
│   ├── routes/
│   │   ├── health.py
│   │   ├── auth.py             # register / login / refresh / me / approve / pending
│   │   ├── projects.py         # list / create / get / update / team / grant / revoke
│   │   ├── tasks.py            # list / create / get / update / delete
│   │   ├── messages.py         # the feedback feed — GET/POST, open to the whole team
│   │   ├── inventory.py        # backend-only for now, see "Deprioritized" below
│   │   ├── drawings.py         # backend-only for now
│   │   ├── finance.py          # backend-only for now
│   │   ├── labour.py           # backend-only for now
│   │   └── calculators.py      # backend-only for now
│   └── static/                 # the actual frontend (see below)
├── tests/                       # 96 tests, all passing — conftest.py has
│                                 # make_user/token_for fixtures every route
│                                 # test file uses
├── requirements.txt
├── run.py                       # dev server: python run.py -> http://localhost:5000
├── wsgi.py                      # production: gunicorn -w 4 wsgi:app
├── pytest.ini
├── .env.example
└── .gitignore
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit SECRET_KEY / JWT_SECRET_KEY
python run.py                # -> http://localhost:5000
pytest -v                    # 96 passed
```

Opening `http://localhost:5000` gets you the real, database-backed app —
not a mockup. First account needs seeding directly (Boss accounts aren't
self-registered, on purpose — see below):

```python
from app import create_app
from app.extensions import db
from app.models import User, UserRole, UserStatus, generate_public_id

app = create_app("development")
with app.app_context():
    db.create_all()
    boss = User(public_id=generate_public_id(UserRole.BOSS), name="Your Name",
                phone="9000000001", role=UserRole.BOSS, status=UserStatus.ACTIVE)
    boss.set_password("changeme123")
    db.session.add(boss)
    db.session.commit()
```

## The frontend

`app/static/` — vanilla JS, no build step, no framework, served by Flask
itself at `/`. Three things worth knowing:

- **No `innerHTML` anywhere.** `dom.js`'s `el()` helper builds every
  element via `createElement`/`textContent`, so interpolated data is never
  parsed as markup — this closes the old app's XSS surface by construction
  rather than by remembering to escape at each of 24 call sites.
- **Every `fetch()` goes through one function.** `api.js`'s `apiRequest()`
  wraps every call in try/catch and shows a toast on failure — the
  frontend mirror of `app/errors.py`'s centralized handler on the backend.
- **Permission checks in the UI are conveniences, not security.** `app.js`
  hides buttons a user can't use (`isManager()`, a task's own assignee
  check), but the actual enforcement is 100% server-side and re-checked on
  every request regardless of what the UI sent. Getting a client-side
  check backwards produces a confusing UI, not a hole.

Built so far: login/register/approve, project list/create, team access grants/revocation, tasks (list/create/update/delete, with the manager-vs-assignee split), feedback, and site progress updates with protected photo uploads, live camera capture, voice notes, editable speech-to-text transcripts, and a keyboard-accessible photo lightbox. Inventory/drawings/finance/labour/calculators have no UI yet (see below).

## Design decisions, and what they replace

**Database: SQLite via SQLAlchemy, WAL mode, no application-level lock.**
The old app serialized every write through one global `threading.Lock()`
acquired in `before_request` with no timeout — a Contractor updating labour
on Site A blocked a PM updating inventory on Site B, and an unhandled
exception before `after_request` could hold the lock forever. This rebuild
turns on SQLite's WAL journal mode instead (`app/__init__.py`), so readers
never block behind writers, and sets a 15s `busy_timeout` so a genuinely
concurrent writer retries instead of erroring. `SQLALCHEMY_DATABASE_URI` is
the only thing that changes to move to Postgres later.

**Site isolation: one join table, one service module.**
`ProjectAccess` is the entire mechanism: a row means "this user may see
this project." `app/services/access_control.py` is the *only* place that
table gets queried. Boss bypasses it entirely; everyone else needs an
explicit grant.

**A third permission shape: ownership, not just role or site.**
`update_task` isn't a `roles_required(...)` one-liner, because the rule
depends on runtime data: Boss/PM may edit any field, but a task's own
assignee — whatever their role — may touch only `status`/`progressPercent`
on a task assigned to *them specifically*. `_resolve_assignee()` reuses
`require_project_access()` directly, so a task can't be assigned to
someone who wouldn't be allowed to see the project it's on.

**Feedback is open, not manager-gated.** Every other write in this app
checks role and/or project access; `messages.py` checks project access
only. Anyone on a site's team — Client included — can post. That's
deliberate: a Client's "the lobby tile colour is wrong" is feedback, not
the "internal management data" the spec excludes them from.

**Passwords: hash-only, no legacy path. Money: `Numeric`, not `Float`.
Errors: one centralized handler, not 31 individual try/excepts.** Same
reasoning as before — see the code comments in `app/models/user.py`,
`app/models/project.py`, and `app/errors.py` respectively.

## Deprioritized on request

Inventory, drawings, finance, labour, and the calculators have working,
tested backends (routes + models + services), reachable at the endpoints
listed above — but no frontend, and no further work planned on them for
now. They're not broken, just paused; each follows the identical pattern
`tasks.py`/`messages.py` already establish, so resuming any one of them is
mechanical, not a redesign.

## Still out of scope

Native mobile packaging, real AI/ML (vs. the old app's hardcoded fake
predictions), drone/GIS integration, true offline-first sync, and
multi-language UI strings were never going to fit a chat-built project —
flagged from the first message of this rebuild, still true now. Dark mode and real drawing-file upload storage are realistic next steps. Site-progress photos and voice notes already use protected persistent upload storage.

## Production hardening added in the final pre-deployment pass

- Auth endpoints are rate-limited with Flask-Limiter. For multiple Gunicorn workers, set `RATELIMIT_STORAGE_URI` to a shared Redis URL.
- Production startup fails fast if strong `SECRET_KEY`, `JWT_SECRET_KEY`, or `DATABASE_URL` are missing.
- Reverse-proxy HTTPS is handled with `ProxyFix`; production responses add HSTS and frame-denial headers.
- `/api/live` is a dependency-free liveness probe. `/api/health` is a readiness probe that verifies both database connectivity and writable media storage.
- Tests disable rate limits to keep the suite deterministic.

### Items that require external infrastructure / user authorization

1. Create/connect Render (or equivalent) and GitHub, then deploy the Blueprint.
2. Provision Redis/Key Value and set `RATELIMIT_STORAGE_URI` for shared production rate limits.
3. Choose a production media strategy. The included Render configuration uses a persistent disk; object storage + malware scanning is recommended for higher scale/risk.
4. Configure an email provider before enabling password-reset/email-verification delivery.
5. If universal speech transcription is required, configure a server transcription provider; browser Web Speech remains the no-credential fallback.
6. Verify camera/microphone behavior on the final HTTPS origin and real phones.
7. Configure managed database backups/retention in the hosting account and external uptime/error monitoring.

## Internet synchronization (Personal Edition)

The real app is server-backed. All users read and write the same API/database; the standalone `interactive-demo.html` is only a demonstration and is not used for shared data.

While logged in, the web client refreshes shared project data and notifications from the server every 15 seconds and immediately reloads affected data after user actions. The top bar displays **Online**, **Syncing…**, or **Offline**. Offline mode is intentionally read-only in practice: requests fail instead of pretending unsynchronized changes were saved.

For a deployed shared app, configure:

- `DATABASE_URL` — one shared PostgreSQL database.
- `STORAGE_BACKEND=s3` — shared private media storage.
- `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` — S3-compatible credentials.

Photos, voice notes and project files remain private. Nirmaan authorizes the requesting user before streaming stored bytes; the storage bucket itself does not need to be public.
