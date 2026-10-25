"""Production entry point. Run with a real WSGI server, e.g.:

    gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app

Do not run this file directly with `python wsgi.py` -- that still uses
Flask's dev server underneath. `-w 4` is fine even against SQLite: WAL mode
(enabled in app/__init__.py) lets those workers' reads proceed without
blocking on each other, and busy_timeout absorbs write contention instead
of erroring immediately. If you outgrow single-writer SQLite, swap
DATABASE_URL to Postgres -- the ORM layer doesn't change.
"""
from app import create_app

app = create_app("production")
