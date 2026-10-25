import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db as _db
from app.models import User, UserStatus, generate_public_id


@pytest.fixture()
def app():
    flask_app = create_app("testing")
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(db):
    """Creates an ACTIVE user directly at the model layer, bypassing the
    register/approve HTTP flow -- that flow is what tests/test_auth.py
    exists to test; route tests for other blueprints just need a logged-in
    user of a given role."""

    def _make(role, phone, name="Test User", status=UserStatus.ACTIVE):
        user = User(
            public_id=generate_public_id(role),
            name=name,
            phone=phone,
            role=role,
            status=status,
        )
        user.set_password("secret123")
        db.session.add(user)
        db.session.commit()
        return user

    return _make


@pytest.fixture()
def token_for(app):
    def _token(user):
        return create_access_token(identity=user)

    return _token
