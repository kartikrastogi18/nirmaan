from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from app.extensions import db
from app.models import Drawing, DrawingCategory, DrawingRevision, RevisionStatus, UserRole
from app.services.access_control import project_access_required, roles_required

drawings_bp = Blueprint("drawings", __name__)

# Boss/PM/Architect can upload and review -- Contractor executes from
# approved drawings but doesn't manage them; Client only ever sees them
# read-only (enforced by the frontend filtering to approved-only, same as
# the earlier prototype's rule, not re-enforced server-side here since a
# Client isn't in this role set at all and has no write routes to reach).
_DRAWING_ROLES = (UserRole.BOSS, UserRole.PROJECT_MANAGER, UserRole.ARCHITECT)


def _bad_request(message: str, **extra):
    return jsonify(error=message, **extra), 400


@drawings_bp.get("/<int:project_id>/drawings")
@jwt_required()
@project_access_required
def list_drawings(project_id):
    drawings = Drawing.query.filter_by(project_id=project_id).order_by(Drawing.name).all()
    if current_user.role == UserRole.CLIENT:
        # Client is intentionally read-only and should only receive drawings
        # that are actually approved for construction. Enforce this on the
        # server rather than relying on frontend filtering.
        visible = []
        for drawing in drawings:
            approved = next((r for r in drawing.revisions if r.status == RevisionStatus.APPROVED), None)
            if approved:
                item = drawing.to_dict()
                item["latestRevision"] = approved.to_dict()
                item["revisionCount"] = sum(1 for r in drawing.revisions if r.status == RevisionStatus.APPROVED)
                visible.append(item)
        return jsonify(drawings=visible)
    return jsonify(drawings=[d.to_dict() for d in drawings])


@drawings_bp.post("/<int:project_id>/drawings")
@jwt_required()
@roles_required(*_DRAWING_ROLES)
@project_access_required
def create_drawing(project_id):
    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")

    name = (data.get("name") or "").strip()
    category = data.get("category")
    file_path = (data.get("filePath") or "").strip()
    if not name:
        return _bad_request("name is required.")
    valid = {c.value for c in DrawingCategory}
    if category not in valid:
        return _bad_request(f"category must be one of {sorted(valid)}.")
    if not file_path:
        return _bad_request("filePath is required.")

    drawing = Drawing(
        project_id=project_id, name=name, category=DrawingCategory(category), uploaded_by=current_user
    )
    db.session.add(drawing)
    db.session.flush()  # assigns drawing.id without a separate round trip

    revision = DrawingRevision(
        drawing_id=drawing.id,
        version_label=data.get("versionLabel") or "Rev 1",
        file_path=file_path,
        uploaded_by=current_user,
    )
    db.session.add(revision)
    db.session.commit()
    return jsonify(drawing=drawing.to_dict()), 201


@drawings_bp.post("/<int:project_id>/drawings/<int:drawing_id>/revisions")
@jwt_required()
@roles_required(*_DRAWING_ROLES)
@project_access_required
def add_revision(project_id, drawing_id):
    drawing = Drawing.query.filter_by(id=drawing_id, project_id=project_id).first()
    if drawing is None:
        return jsonify(error="No such drawing."), 404

    data = request.get_json(silent=True)
    if not data:
        return _bad_request("Request body must be JSON.")
    file_path = (data.get("filePath") or "").strip()
    version_label = (data.get("versionLabel") or "").strip()
    if not file_path:
        return _bad_request("filePath is required.")
    if not version_label:
        return _bad_request("versionLabel is required.")

    revision = DrawingRevision(
        drawing_id=drawing.id, version_label=version_label, file_path=file_path, uploaded_by=current_user
    )
    db.session.add(revision)
    db.session.commit()
    return jsonify(drawing=drawing.to_dict()), 201


@drawings_bp.patch("/<int:project_id>/drawings/<int:drawing_id>/revisions/<int:revision_id>")
@jwt_required()
@roles_required(*_DRAWING_ROLES)
@project_access_required
def review_revision(project_id, drawing_id, revision_id):
    revision = DrawingRevision.query.filter_by(id=revision_id, drawing_id=drawing_id).first()
    if revision is None or revision.drawing.project_id != project_id:
        return jsonify(error="No such drawing revision."), 404

    data = request.get_json(silent=True)
    status = data.get("status") if data else None
    valid = {s.value for s in RevisionStatus} - {"pending_review"}
    if status not in valid:
        return _bad_request(f"status must be one of {sorted(valid)}.")

    revision.status = RevisionStatus(status)
    revision.review_notes = data.get("reviewNotes")
    revision.reviewed_by = current_user
    db.session.commit()
    return jsonify(revision=revision.to_dict())
