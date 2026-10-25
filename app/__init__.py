from __future__ import annotations

import os

from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.config import config_map
from app.extensions import bcrypt, db, jwt, migrate, limiter


def create_app(env: str | None = None) -> Flask:
    env = env or os.environ.get("FLASK_ENV", "development")
    # static_url_path="" serves everything in app/static/ from the root, so
    # static/index.html is reachable at "/" and static/js/app.js at
    # "/js/app.js" -- no separate frontend server/build step needed for
    # what's intentionally a thin, no-build-tool UI.
    app = Flask(__name__, instance_relative_config=True, static_url_path="")
    app.config.from_object(config_map[env])
    if env == "production":
        _validate_production_config(app)
        # Render/most PaaS terminate TLS at a reverse proxy. Trust exactly one
        # forwarding hop so Flask sees the original HTTPS scheme/client host.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Persistent Render disk can be mounted at /var/data; otherwise retain local behavior.
    instance_override = os.environ.get("INSTANCE_PATH")
    if instance_override:
        app.instance_path = instance_override
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    _configure_sqlite_concurrency(app)

    # Import models so their tables are registered on db.metadata before any
    # create_all() / migration runs. Import happens inside the factory (not
    # at module load time) to avoid circular imports with `db`.
    with app.app_context():
        from app import models  # noqa: F401

    _configure_jwt(app)

    from app.errors import register_error_handlers

    register_error_handlers(app)

    from app.routes.auth import auth_bp
    from app.routes.calculators import calculators_bp
    from app.routes.drawings import drawings_bp
    from app.routes.finance import finance_bp
    from app.routes.health import health_bp
    from app.routes.inventory import inventory_bp
    from app.routes.labour import labour_bp
    from app.routes.messages import messages_bp
    from app.routes.personal import personal_bp
    from app.routes.projects import projects_bp
    from app.routes.progress import progress_bp
    from app.routes.tasks import tasks_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(projects_bp, url_prefix="/api/projects")
    app.register_blueprint(progress_bp, url_prefix="/api")
    app.register_blueprint(tasks_bp, url_prefix="/api/projects")
    app.register_blueprint(inventory_bp, url_prefix="/api/projects")
    app.register_blueprint(drawings_bp, url_prefix="/api/projects")
    app.register_blueprint(finance_bp, url_prefix="/api/projects")
    app.register_blueprint(labour_bp, url_prefix="/api/projects")
    app.register_blueprint(messages_bp, url_prefix="/api/projects")
    app.register_blueprint(personal_bp, url_prefix="/api")
    app.register_blueprint(calculators_bp, url_prefix="/api/calculators")

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(self)")
        if env == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
        return response

    return app


def _configure_jwt(app: Flask) -> None:
    """Tells Flask-JWT-Extended how to turn a User into a token identity and
    back again, and makes its built-in error responses match the
    {"error": "..."} shape the rest of the API uses instead of its default
    {"msg": "..."}."""
    from app.extensions import jwt

    @jwt.user_identity_loader
    def user_identity_lookup(user):
        # Subjects must be strings; the id is cast back to int on the way
        # back in (see user_lookup_callback and routes/auth.py's refresh()).
        return str(user.id)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        from app.models import User, UserStatus

        user = db.session.get(User, int(jwt_data["sub"]))
        return user if user is not None and user.status == UserStatus.ACTIVE else None

    @jwt.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_payload):
        return jsonify(error="Session expired. Please log in again."), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(_reason):
        return jsonify(error="Invalid authentication token."), 401

    @jwt.unauthorized_loader
    def missing_token_callback(_reason):
        return jsonify(error="Authentication required."), 401


def _configure_sqlite_concurrency(app: Flask) -> None:
    """SQLite has no concept of a client-side mutex -- the old codebase's
    bug was inventing one (a single global threading.Lock wrapping every
    write route, acquired with no timeout). The correct fix is to let the
    database engine itself handle concurrency:

      - WAL journal mode: readers no longer block behind writers.
      - foreign_keys=ON: SQLite doesn't enforce FK constraints unless told to,
        per-connection, every time.
      - busy_timeout: a writer that finds the DB locked retries for up to
        this many ms instead of raising "database is locked" immediately.

    This block is a no-op for any non-SQLite SQLALCHEMY_DATABASE_URI, so
    swapping to Postgres later (see README) doesn't require removing it.
    """
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        return

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()


def _validate_production_config(app: Flask) -> None:
    """Fail fast instead of accidentally deploying with development secrets."""
    bad_markers = ("dev-secret", "dev-jwt-secret", "change-me")
    for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
        value = str(app.config.get(key) or "")
        if len(value) < 32 or any(marker in value for marker in bad_markers):
            raise RuntimeError(f"{key} must be a strong production secret (32+ characters).")

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        raise RuntimeError("DATABASE_URL is required in production; SQLite fallback is not allowed for deployment.")

    rate_store = str(app.config.get("RATELIMIT_STORAGE_URI") or "")
    if rate_store == "memory://":
        app.logger.warning(
            "Rate limiting is using memory://; configure RATELIMIT_STORAGE_URI=redis://... "
            "for shared limits across multiple Gunicorn workers."
        )
