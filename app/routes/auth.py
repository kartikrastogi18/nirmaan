from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    current_user,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.exc import IntegrityError
import secrets

from app.extensions import db, limiter
from app.models import User, UserRole, UserStatus, Project, ProjectAccess, generate_public_id
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
    """Self-registration with username or phone. Accounts activate immediately."""
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    name = (data.get("name") or "").strip()
    raw_phone = (data.get("phone") or "").strip()
    phone = _clean_phone(raw_phone)
    raw_username = (data.get("username") or "").strip().lower()
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

    username = raw_username or phone

    try:
        user = User(
            public_id=generate_public_id(role_enum),
            username=username,
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
        return _bad_request("That phone number or username is already registered.")

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

    identifier = (data.get("username") or data.get("phone") or data.get("identifier") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return _bad_request("Username/phone and password are required.")

    clean_p = _clean_phone(identifier)
    candidates = {identifier, clean_p}
    if clean_p.startswith("+91"):
        candidates.add(clean_p[3:])
    elif len(clean_p) == 10:
        candidates.add("+91" + clean_p)

    user = User.query.filter(
        (User.username == identifier.lower()) |
        (User.phone.in_(candidates)) |
        (User.name.ilike(identifier))
    ).first()

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


@auth_bp.get("/users")
@jwt_required()
@roles_required(UserRole.BOSS)
def list_users():
    """Boss-only: List all provisioned users and their assigned sites."""
    users = User.query.order_by(User.id.asc()).all()
    result = []
    for u in users:
        ud = u.to_public_dict()
        ud["assignedProjects"] = [
            {"id": pa.project.id, "name": pa.project.name, "siteCode": pa.project.site_code}
            for pa in u.project_access if pa.project
        ]
        result.append(ud)
    return jsonify(users=result)


@auth_bp.post("/users")
@jwt_required()
@roles_required(UserRole.BOSS)
def create_user_by_boss():
    """Boss-only: Provision a new user with specific username, role, password, and assigned site."""
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    username = (data.get("username") or "").strip().lower()
    name = (data.get("name") or "").strip() or username
    role = (data.get("role") or "").strip().lower()
    password = data.get("password") or ""
    project_id = data.get("projectId")
    phone = (data.get("phone") or "").strip()

    if not username or len(username) < 2:
        return _bad_request("Username must be at least 2 characters.")
    if role not in _VALID_ROLES:
        return _bad_request(f"role must be one of {sorted(_VALID_ROLES)}.")
    if not password or len(password) < 6:
        return _bad_request("Password must be at least 6 characters.")

    existing_user = User.query.filter(User.username == username).first()
    if existing_user:
        return _bad_request(f"Username '{username}' is already taken.")

    if not phone:
        phone = f"USR_{secrets.token_hex(4)}"
    else:
        if User.query.filter_by(phone=phone).first():
            return _bad_request(f"Phone number '{phone}' is already registered.")

    role_enum = UserRole(role)
    try:
        user = User(
            public_id=generate_public_id(role_enum),
            username=username,
            name=name,
            phone=phone,
            role=role_enum,
            status=UserStatus.ACTIVE,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # If a specific project was selected, grant access immediately
        if project_id:
            proj = db.session.get(Project, int(project_id))
            if proj:
                access = ProjectAccess(
                    user_id=user.id,
                    project_id=proj.id,
                    granted_by_id=current_user.id
                )
                db.session.add(access)

        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return _bad_request(str(exc))
    except IntegrityError:
        db.session.rollback()
        return _bad_request("That username or phone number is already registered.")

    return jsonify(
        message=f"User {user.username} created successfully.",
        user=user.to_public_dict(),
    ), 201
