import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class BaseConfig:
    # Defaults are only for a from-scratch `python run.py` with no .env yet --
    # .env.example documents generating real ones. Padded past 32 bytes even
    # here so HS256 doesn't warn (or get weaker) if someone forgets to
    # override these before actually deploying.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-before-deploying-00000")
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", "dev-jwt-secret-change-me-before-deploying-00000"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLite-specific: wait up to 15s for a write lock instead of raising
    # "database is locked" immediately under concurrent writes.
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 15}}

    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB upload ceiling (drawings/photos)
    MAX_PHOTO_COUNT = 12
    UPLOAD_ROOT = os.environ.get("UPLOAD_ROOT")
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")
    S3_REGION = os.environ.get("S3_REGION", "auto")
    S3_BUCKET = os.environ.get("S3_BUCKET")
    S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    PREFERRED_URL_SCHEME = "https"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        BASE_DIR, "instance", "totalworks.db"
    )


class TestingConfig(BaseConfig):
    TESTING = True
    RATELIMIT_ENABLED = False
    # In-memory DB per test run; see tests/conftest.py
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    # Flask defaults this to True whenever TESTING is True, which makes an
    # unhandled exception propagate to the test client as a raw Python
    # exception instead of going through our error handlers. Turning it off
    # lets tests actually exercise the same clean-JSON-500 behavior
    # production gets -- see tests/test_errors.py.
    PROPAGATE_EXCEPTIONS = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "totalworks.db"),
    ).replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"connect_args": {"timeout": 15}}
        if SQLALCHEMY_DATABASE_URI.startswith("sqlite") else {"pool_pre_ping": True}
    )


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
