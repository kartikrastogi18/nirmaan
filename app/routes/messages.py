from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import Message
from app.services.access_control import project_access_required
from app.services.activity import notify_project, record

messages_bp = Blueprint("messages", __name__)

_MAX_BODY_LENGTH = 2000


def _bad_request(message: str, **extra):
    return jsonify(error=message, **extra), 400


@messages_bp.get("/<int:project_id>/messages")
@jwt_required()
@project_access_required
def list_messages(project_id):
    messages = (
        Message.query.filter_by(project_id=project_id).order_by(Message.created_at.asc()).all()
    )
    return jsonify(messages=[m.to_dict() for m in messages])


@messages_bp.post("/<int:project_id>/messages")
@jwt_required()
@project_access_required
def create_message(project_id):
    """Anyone with project access can post -- feedback is exactly the open,
    whole-team communication the spec describes ('project-specific
    discussion channels'), not a manager-gated write like tasks or
    inventory. Client is deliberately included: 'the tile colour in the
    lobby doesn't match what we agreed' is feedback, not 'internal
    management data' the spec excludes them from."""
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    body = (data.get("body") or "").strip()
    if not body:
        return _bad_request("body is required.")
    if len(body) > _MAX_BODY_LENGTH:
        return _bad_request(f"body must be {_MAX_BODY_LENGTH} characters or fewer.")

    message = Message(project_id=project_id, sender=current_user, body=body)
    db.session.add(message)
    db.session.flush()
    record(current_user, project_id, "feedback.post", "Posted project feedback", "message", message.id)
    notify_project(project_id, f"{current_user.name} posted feedback", "feedback", exclude_user_id=current_user.id)
    db.session.commit()
    return jsonify(message=message.to_dict()), 201
