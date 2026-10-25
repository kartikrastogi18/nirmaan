from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    current_user,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.exc import IntegrityError

from app.extensions import db, limiter
from app.models import User, UserRole, UserStatus, generate_public_id
from app.services.access_control import roles_required

auth_bp = Blueprint("auth", __name__)

_VALID_ROLES = {r.value for r in UserRole}


def _bad_request(message: str, **extra):
    return jsonify(error=message, **extra), 400


def _clean_phone(raw: str) -> str:
    """Normalize phone number by stripping spaces, hyphens, and punctuation."""
    if not raw:
        return ""
    return "".join(c for c in raw.strip() if c.isdigit() or c == "+")


@auth_bp.post("/register")
@limiter.limit("500 per hour")
def register():
    """Self-registration. Accounts activate immediately without requiring boss approval."""
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    name = (data.get("name") or "").strip()
    raw_phone = (data.get("phone") or "").strip()
    phone = _clean_phone(raw_phone)
    password = data.get("password") or ""
    role = (data.get("role") or "").strip().lower()

    if not name or len(name) < 2:
        return _bad_request("Name is required.")
    if not phone or len(phone) < 8:
        return _bad_request("A valid phone number (at least 8 digits) is required.")
    if role not in _VALID_ROLES:
        return _bad_request(f"role must be one of {sorted(_VALID_ROLES)}.")

    role_enum = UserRole(role)

    # Check duplicate phone before attempting insert
    existing = User.query.filter((User.phone == phone) | (User.phone == raw_phone)).first()
    if existing:
        return _bad_request("That phone number is already registered.")

    try:
        user = User(
            public_id=generate_public_id(role_enum),
            name=name,
            phone=phone,
            role=role_enum,
            status=UserStatus.ACTIVE,  # Instant access: no approval required
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except ValueError as exc:
        # From User.set_password()'s length check.
        db.session.rollback()
        return _bad_request(str(exc))
    except IntegrityError:
        db.session.rollback()
        return _bad_request("That phone number is already registered.")

    access_token = create_access_token(identity=user)
    refresh_token = create_refresh_token(identity=user)

    return (
        jsonify(
            message="Registered successfully! Your account is active.",
            user=user.to_public_dict(),
            access_token=access_token,
            refresh_token=refresh_token,
        ),
        201,
    )


@auth_bp.post("/login")
@limiter.limit("500 per hour")
def login():
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    raw_phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""

    if not raw_phone or not password:
        return _bad_request("Phone number and password are required.")

    clean_p = _clean_phone(raw_phone)
    candidates = {raw_phone, clean_p}
    if clean_p.startswith("+91"):
        candidates.add(clean_p[3:])
    elif len(clean_p) == 10:
        candidates.add("+91" + clean_p)

    user = User.query.filter(User.phone.in_(candidates)).first()

    if user is None or not user.check_password(password):
        return jsonify(error="Invalid phone number or password."), 401

    # Auto-activate any pending account so no one is blocked by approval
    if user.status == UserStatus.PENDING:
        user.status = UserStatus.ACTIVE
        db.session.commit()

    if user.status == UserStatus.SUSPENDED:
        return jsonify(error="This account has been suspended."), 403

    return jsonify(
        access_token=create_access_token(identity=user),
        refresh_token=create_refresh_token(identity=user),
        user=user.to_public_dict(),
    )


@auth_bp.post("/refresh")
@limiter.limit("100 per minute")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if user is None or user.status != UserStatus.ACTIVE:
        return jsonify(error="Account not found or inactive."), 401
    return jsonify(access_token=create_access_token(identity=user))


@auth_bp.get("/me")
@jwt_required()
def me():
    return jsonify(user=current_user.to_public_dict())


@auth_bp.get("/pending")
@jwt_required()
@roles_required(UserRole.BOSS)
def list_pending():
    pending = User.query.filter_by(status=UserStatus.PENDING).order_by(User.created_at).all()
    return jsonify(users=[u.to_public_dict() for u in pending])


@auth_bp.post("/users/<public_id>/approve")
@jwt_required()
@roles_required(UserRole.BOSS)
def approve_user(public_id):
    user = User.query.filter_by(public_id=public_id).first()
    if user is None:
        return jsonify(error="No such user."), 404
    user.status = UserStatus.ACTIVE
    db.session.commit()
    return jsonify(message=f"{user.name} approved.", user=user.to_public_dict())
