from datetime import date
import math

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import Project, ProjectAccess, ProjectStatus, User, UserRole, UserStatus
from app.services.activity import notify_project, record
from app.services.access_control import (
    project_access_required,
    roles_required,
    visible_projects_query,
)

projects_bp = Blueprint("projects", __name__)


def _bad_request(message: str, **extra):
    return jsonify(error=message, **extra), 400


def _parse_date(value, field_name: str):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an ISO date (YYYY-MM-DD).") from exc


@projects_bp.get("")
@jwt_required()
def list_projects():
    """Every project current_user can see. Boss gets all of them; everyone
    else only what they hold a ProjectAccess grant for -- the isolation
    rule proven in tests/test_models.py, now exercised through a live
    route instead of only at the model layer."""
    projects = visible_projects_query(current_user).order_by(Project.site_code).all()
    return jsonify(projects=[p.to_dict() for p in projects])


@projects_bp.post("")
@jwt_required()
@roles_required(UserRole.BOSS)
def create_project():
    """Matches the spec: 'Boss: Can create and manage multiple construction
    projects.' Nobody else gets a create route at all."""
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    site_code = (data.get("siteCode") or "").strip().upper()
    name = (data.get("name") or "").strip()
    if not site_code:
        return _bad_request("siteCode is required.")
    if len(site_code) > 10:
        return _bad_request("siteCode must be 10 characters or fewer.")
    if not name:
        return _bad_request("name is required.")
    if len(name) > 200:
        return _bad_request("name must be 200 characters or fewer.")

    try:
        budget = float(data.get("budget") or 0)
        if not math.isfinite(budget):
            return _bad_request("budget must be a finite number.")
        if budget < 0:
            return _bad_request("budget cannot be negative.")
        start_date = _parse_date(data.get("startDate"), "startDate")
        target_end_date = _parse_date(data.get("targetEndDate"), "targetEndDate")
        if start_date and target_end_date and target_end_date < start_date:
            return _bad_request("targetEndDate cannot be before startDate.")
        project = Project(
            site_code=site_code,
            name=name,
            location=(data.get("location") or "").strip() or None,
            project_type=(data.get("projectType") or "").strip() or None,
            description=(data.get("description") or "").strip() or None,
            budget=budget,
            start_date=start_date,
            target_end_date=target_end_date,
            created_by=current_user,
        )
    except ValueError as exc:
        return _bad_request(str(exc))

    db.session.add(project)
    db.session.commit()  # duplicate siteCode -> IntegrityError -> 409 (app/errors.py)
    return jsonify(project=project.to_dict()), 201


@projects_bp.get("/<int:project_id>")
@jwt_required()
@project_access_required
def get_project(project_id):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify(error="No such project."), 404
    return jsonify(project=project.to_dict())


@projects_bp.patch("/<int:project_id>")
@jwt_required()
@roles_required(UserRole.BOSS, UserRole.PROJECT_MANAGER)
@project_access_required
def update_project(project_id):
    """Two independent gates, both required: roles_required checks *what
    kind* of user this is, project_access_required checks *whether they're
    assigned to this specific site*. A PM with no grant for this project is
    still refused; a Contractor who IS assigned is still refused. Neither
    check alone is sufficient -- see tests/test_projects.py for both halves
    proven separately."""
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify(error="No such project."), 404

    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    financial_fields = {"budget", "spent"}
    if current_user.role != UserRole.BOSS and financial_fields.intersection(data):
        return jsonify(error="Only Boss/Admin can edit project budget or spending."), 403

    if "progressPercent" in data:
        return _bad_request("Overall progress is calculated automatically from task progress.")

    try:
        if "name" in data:
            project.name = (data["name"] or "").strip() or project.name
        if "location" in data:
            project.location = data["location"]
        if "projectType" in data:
            project.project_type = data["projectType"]
        if "description" in data:
            project.description = data["description"]
        if "status" in data:
            valid = {s.value for s in ProjectStatus}
            if data["status"] not in valid:
                return _bad_request(f"status must be one of {sorted(valid)}.")
            project.status = ProjectStatus(data["status"])
        if "budget" in data:
            budget = float(data["budget"])
            if not math.isfinite(budget):
                return _bad_request("budget must be a finite number.")
            if budget < 0:
                return _bad_request("budget cannot be negative.")
            project.budget = budget
        if "spent" in data:
            spent = float(data["spent"])
            if not math.isfinite(spent):
                return _bad_request("spent must be a finite number.")
            if spent < 0:
                return _bad_request("spent cannot be negative.")
            project.spent = spent
        if "plannedProgressPercent" in data:
            pct = data["plannedProgressPercent"]
            if not isinstance(pct, (int, float)) or isinstance(pct, bool) or not 0 <= pct <= 100:
                return _bad_request("plannedProgressPercent must be a number between 0 and 100.")
            project.planned_progress_percent = pct
        if "startDate" in data:
            project.start_date = _parse_date(data["startDate"], "startDate")
        if "targetEndDate" in data:
            project.target_end_date = _parse_date(data["targetEndDate"], "targetEndDate")
        if "actualEndDate" in data:
            project.actual_end_date = _parse_date(data["actualEndDate"], "actualEndDate")
        if project.start_date and project.target_end_date and project.target_end_date < project.start_date:
            return _bad_request("targetEndDate cannot be before startDate.")
    except ValueError as exc:
        return _bad_request(str(exc))

    db.session.commit()
    return jsonify(project=project.to_dict())


@projects_bp.get("/<int:project_id>/team")
@jwt_required()
@project_access_required
def list_team(project_id):
    grants = ProjectAccess.query.filter_by(project_id=project_id).all()
    return jsonify(team=[grant.user.to_public_dict() for grant in grants])


@projects_bp.post("/<int:project_id>/access")
@jwt_required()
@roles_required(UserRole.BOSS, UserRole.PROJECT_MANAGER)
@project_access_required
def grant_access(project_id):
    """Bosses can grant access globally; Project Managers can grant access
    only on projects they are themselves assigned to."""
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify(error="No such project."), 404

    data = request.get_json(silent=True)
    if not data or not data.get("userId"):
        return _bad_request("userId is required.")

    user = User.query.filter_by(public_id=data["userId"]).first()
    if user is None:
        return jsonify(error="No such user."), 404
    if user.role == UserRole.BOSS:
        return _bad_request("Boss already has access to every project.")
    if user.status != UserStatus.ACTIVE:
        return _bad_request("Only approved active users can be added to a project.")

    if ProjectAccess.query.filter_by(user_id=user.id, project_id=project.id).first():
        return _bad_request(f"{user.name} already has access to this project.")

    db.session.add(ProjectAccess(user_id=user.id, project_id=project.id, granted_by_id=current_user.id))
    record(current_user, project_id, "access.grant", f"Granted project access to {user.name}", "user", user.id)
    notify_project(project_id, f"You were added to {project.name}", "access", only_user_id=user.id)
    db.session.commit()
    return jsonify(message=f"{user.name} granted access to {project.name}."), 201


@projects_bp.delete("/<int:project_id>/access/<user_public_id>")
@jwt_required()
@roles_required(UserRole.BOSS)
def revoke_access(project_id, user_public_id):
    user = User.query.filter_by(public_id=user_public_id).first()
    if user is None:
        return jsonify(error="No such user."), 404

    grant = ProjectAccess.query.filter_by(user_id=user.id, project_id=project_id).first()
    if grant is None:
        return jsonify(error=f"{user.name} doesn't have access to this project."), 404

    db.session.delete(grant)
    db.session.commit()
    return jsonify(message=f"Access revoked for {user.name}.")
