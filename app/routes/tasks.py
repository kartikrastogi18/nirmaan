from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import Project, Task, TaskPriority, TaskStatus, User, UserRole, UserStatus
from app.services.access_control import project_access_required, require_project_access, roles_required
from app.services.activity import notify_project, record

tasks_bp = Blueprint("tasks", __name__)

_MANAGER_ROLES = (UserRole.BOSS, UserRole.PROJECT_MANAGER)


def _bad_request(message: str, **extra):
    return jsonify(error=message, **extra), 400


def _parse_date(value, field_name: str):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an ISO date (YYYY-MM-DD).") from exc




def _recalculate_project_progress(project_id: int) -> None:
    project = db.session.get(Project, project_id)
    if project is None:
        return
    tasks = Task.query.filter_by(project_id=project_id).all()
    project.progress_percent = round(sum(t.progress_percent for t in tasks) / len(tasks), 1) if tasks else 0

def _resolve_assignee(project_id: int, assignee_public_id):
    """Looks up a user by public id and confirms they actually hold access
    to this project -- reuses the exact rule access_control.py enforces
    everywhere else, so a task can never be assigned to someone who
    wouldn't even be allowed to see it."""
    if not assignee_public_id:
        return None
    user = User.query.filter_by(public_id=assignee_public_id).first()
    if user is None:
        raise ValueError("No such user to assign.")
    if user.status != UserStatus.ACTIVE:
        raise ValueError("Only approved active users can be assigned tasks.")
    if not require_project_access(user, project_id):
        raise ValueError(f"{user.name} doesn't have access to this project and can't be assigned.")
    return user


@tasks_bp.get("/<int:project_id>/tasks")
@jwt_required()
@project_access_required
def list_tasks(project_id):
    query = Task.query.filter_by(project_id=project_id)

    status = request.args.get("status")
    if status:
        valid = {s.value for s in TaskStatus}
        if status not in valid:
            return _bad_request(f"status must be one of {sorted(valid)}.")
        query = query.filter_by(status=TaskStatus(status))

    if request.args.get("mine") == "true":
        query = query.filter_by(assignee_id=current_user.id)

    tasks = query.order_by(Task.due_date.is_(None), Task.due_date).all()
    return jsonify(tasks=[t.to_dict() for t in tasks])


@tasks_bp.post("/<int:project_id>/tasks")
@jwt_required()
@roles_required(*_MANAGER_ROLES)
@project_access_required
def create_task(project_id):
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    title = (data.get("title") or "").strip()
    if not title:
        return _bad_request("title is required.")

    priority = data.get("priority", TaskPriority.MEDIUM.value)
    if priority not in {p.value for p in TaskPriority}:
        return _bad_request(f"priority must be one of {sorted(p.value for p in TaskPriority)}.")

    try:
        assignee = _resolve_assignee(project_id, data.get("assigneeId"))
        task = Task(
            project_id=project_id,
            wbs_code=data.get("wbsCode"),
            title=title,
            description=data.get("description"),
            priority=TaskPriority(priority),
            due_date=_parse_date(data.get("dueDate"), "dueDate"),
            due_time=(data.get("dueTime") or "").strip() or None,
            assignee=assignee,
            created_by=current_user,
        )
    except ValueError as exc:
        return _bad_request(str(exc))

    db.session.add(task)
    db.session.flush()
    record(current_user, project_id, "task.create", f"Created task: {task.title}", "task", task.id)
    if assignee:
        notify_project(project_id, f"New task assigned: {task.title}", "task", only_user_id=assignee.id)
    _recalculate_project_progress(project_id)
    db.session.commit()
    return jsonify(task=task.to_dict()), 201


@tasks_bp.get("/<int:project_id>/tasks/<int:task_id>")
@jwt_required()
@project_access_required
def get_task(project_id, task_id):
    task = Task.query.filter_by(id=task_id, project_id=project_id).first()
    if task is None:
        return jsonify(error="No such task."), 404
    return jsonify(task=task.to_dict())


@tasks_bp.patch("/<int:project_id>/tasks/<int:task_id>")
@jwt_required()
@project_access_required
def update_task(project_id, task_id):
    """Deliberately NOT a roles_required() decorator -- the permission here
    depends on runtime data (which specific task, who it's assigned to),
    not just the caller's role, so it can't be expressed declaratively the
    way create/delete below can.

    Boss/PM may change any field. The task's own assignee -- regardless of
    their role -- may update only status/progressPercent on a task assigned
    to them: this is the Contractor's "update work progress" from the spec,
    and it generalizes correctly to an Architect assigned a review task
    too, rather than being hardcoded to one role name."""
    task = Task.query.filter_by(id=task_id, project_id=project_id).first()
    if task is None:
        return jsonify(error="No such task."), 404

    is_manager = current_user.role in _MANAGER_ROLES
    is_assignee = task.assignee_id == current_user.id
    if not is_manager and not is_assignee:
        return jsonify(error="You can only update tasks assigned to you."), 403

    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    if not is_manager:
        disallowed = sorted(set(data.keys()) - {"status", "progressPercent"})
        if disallowed:
            return _bad_request(
                "You can only update status and progressPercent on a task assigned to you.",
                disallowedFields=disallowed,
            )

    try:
        if "title" in data:
            title = (data["title"] or "").strip()
            if not title:
                return _bad_request("title cannot be empty.")
            task.title = title
        if "description" in data:
            task.description = data["description"]
        if "wbsCode" in data:
            task.wbs_code = data["wbsCode"]
        if "priority" in data:
            valid = {p.value for p in TaskPriority}
            if data["priority"] not in valid:
                return _bad_request(f"priority must be one of {sorted(valid)}.")
            task.priority = TaskPriority(data["priority"])
        if "dueDate" in data:
            task.due_date = _parse_date(data["dueDate"], "dueDate")
        if "dueTime" in data:
            due_time = (data["dueTime"] or "").strip()
            if due_time and (len(due_time) != 5 or due_time[2] != ":"):
                return _bad_request("dueTime must be HH:MM.")
            task.due_time = due_time or None
        if "assigneeId" in data:
            task.assignee = _resolve_assignee(project_id, data["assigneeId"])
        if "status" in data:
            valid = {s.value for s in TaskStatus}
            if data["status"] not in valid:
                return _bad_request(f"status must be one of {sorted(valid)}.")
            task.status = TaskStatus(data["status"])
        if "progressPercent" in data:
            pct = data["progressPercent"]
            if not isinstance(pct, (int, float)) or isinstance(pct, bool) or not (0 <= pct <= 100):
                return _bad_request("progressPercent must be a number between 0 and 100.")
            task.progress_percent = pct
    except ValueError as exc:
        return _bad_request(str(exc))

    record(current_user, project_id, "task.update", f"Updated task: {task.title}", "task", task.id)
    _recalculate_project_progress(project_id)
    db.session.commit()
    return jsonify(task=task.to_dict())


@tasks_bp.delete("/<int:project_id>/tasks/<int:task_id>")
@jwt_required()
@roles_required(*_MANAGER_ROLES)
@project_access_required
def delete_task(project_id, task_id):
    task = Task.query.filter_by(id=task_id, project_id=project_id).first()
    if task is None:
        return jsonify(error="No such task."), 404

    title = task.title
    record(current_user, project_id, "task.delete", f"Deleted task: {title}", "task", task.id)
    db.session.delete(task)
    db.session.flush()
    _recalculate_project_progress(project_id)
    db.session.commit()
    return jsonify(message="Task deleted.")
