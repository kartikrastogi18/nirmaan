from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()
jwt = JWTManager()

# Uses Redis in production when RATELIMIT_STORAGE_URI is configured; tests/dev
# can use the in-memory backend. Route-specific limits live next to the routes.
limiter = Limiter(key_func=get_remote_address, default_limits=[])
