import json
import io
import os
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import current_user, jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (AuditLog, Drawing, Message, Notification, ProgressLog, Project,
                        ProjectAccess, ProjectFile, Task, UserRole)
from app.services.access_control import project_access_required, roles_required
from app.services import storage

personal_bp = Blueprint("personal", __name__)
ALLOWED_FILE_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "doc", "docx", "xls", "xlsx", "csv", "txt"}
MAX_FILE_BYTES = 15 * 1024 * 1024


def _upload_root():
    root = current_app.config.get("UPLOAD_ROOT") or os.path.join(current_app.instance_path, "uploads")
    path = Path(root) / "files"
    path.mkdir(parents=True, exist_ok=True)
    return path


@personal_bp.get("/notifications")
@jwt_required()
def notifications():
    rows = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return jsonify(notifications=[{
        "id": n.id, "projectId": n.project_id, "kind": n.kind, "text": n.text,
        "isRead": n.is_read, "createdAt": n.created_at.isoformat()
    } for n in rows])


@personal_bp.patch("/notifications/<int:notification_id>/read")
@jwt_required()
def read_notification(notification_id):
    n = Notification.query.filter_by(id=notification_id, recipient_id=current_user.id).first()
    if not n:
        return jsonify(error="No such notification."), 404
    n.is_read = True
    db.session.commit()
    return jsonify(ok=True)


@personal_bp.get("/projects/<int:project_id>/activity")
@jwt_required()
@project_access_required
def activity(project_id):
    rows = AuditLog.query.filter_by(project_id=project_id).order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify(activity=[{
        "id": a.id, "action": a.action, "detail": a.detail,
        "actor": a.actor.to_public_dict() if a.actor else None,
        "createdAt": a.created_at.isoformat()
    } for a in rows])


@personal_bp.get("/projects/<int:project_id>/search")
@jwt_required()
@project_access_required
def search_project(project_id):
    q = (request.args.get("q") or "").strip().lower()
    if len(q) > 200:
        return jsonify(error="Search query must be 200 characters or fewer."), 400
    if len(q) < 2:
        return jsonify(results=[])
    results = []
    for t in Task.query.filter_by(project_id=project_id).all():
        if q in (t.title or "").lower() or q in (t.description or "").lower():
            results.append({"type": "task", "id": t.id, "title": t.title, "text": t.description or ""})
    for m in Message.query.filter_by(project_id=project_id).all():
        if q in (m.body or "").lower():
            results.append({"type": "feedback", "id": m.id, "title": m.sender.name if m.sender else "Feedback", "text": m.body})
    for p in ProgressLog.query.filter_by(project_id=project_id).all():
        hay = " ".join([p.title or "", p.description or "", p.audio_transcript or ""]).lower()
        if q in hay:
            results.append({"type": "site update", "id": p.id, "title": p.title, "text": p.description or p.audio_transcript or ""})
    for f in ProjectFile.query.filter_by(project_id=project_id).all():
        if q in f.original_name.lower():
            results.append({"type": "file", "id": f.id, "title": f.original_name, "text": "Project file"})
    return jsonify(results=results[:50])


@personal_bp.get("/projects/<int:project_id>/files")
@jwt_required()
@project_access_required
def list_files(project_id):
    rows = ProjectFile.query.filter_by(project_id=project_id).order_by(ProjectFile.created_at.desc()).all()
    return jsonify(files=[f.to_dict() for f in rows])


@personal_bp.post("/projects/<int:project_id>/files")
@jwt_required()
@roles_required(UserRole.BOSS, UserRole.PROJECT_MANAGER, UserRole.ARCHITECT, UserRole.CONTRACTOR)
@project_access_required
def upload_file(project_id):
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="Choose a file to upload."), 400
    original = secure_filename(f.filename)
    if not original:
        return jsonify(error="File name is invalid."), 400
    if len(original) > 255:
        return jsonify(error="File name must be 255 characters or fewer."), 400
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_FILE_EXTENSIONS:
        return jsonify(error="Unsupported file type."), 400
    data = f.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        return jsonify(error="File must be 15 MB or smaller."), 413
    if not data:
        return jsonify(error="File cannot be empty."), 400
    stored = f"{uuid.uuid4().hex}.{ext}"
    storage.put_bytes(f"files/{stored}", data, f.mimetype)
    row = ProjectFile(project_id=project_id, uploaded_by_id=current_user.id, original_name=original,
                      stored_name=stored, mime_type=f.mimetype, size_bytes=len(data))
    db.session.add(row)
    db.session.add(AuditLog(actor_id=current_user.id, project_id=project_id, action="file.upload",
                            entity_type="project_file", detail=f"Uploaded {original}"))
    db.session.commit()
    return jsonify(file=row.to_dict()), 201


@personal_bp.get("/projects/<int:project_id>/files/<int:file_id>")
@jwt_required()
@project_access_required
def download_file(project_id, file_id):
    row = ProjectFile.query.filter_by(id=file_id, project_id=project_id).first()
    if not row:
        return jsonify(error="No such file."), 404
    key = f"files/{row.stored_name}"
    if not storage.exists(key):
        return jsonify(error="Stored file is missing."), 404
    return send_file(io.BytesIO(storage.get_bytes(key)), mimetype=row.mime_type or "application/octet-stream", as_attachment=True, download_name=row.original_name)


@personal_bp.get("/projects/<int:project_id>/export")
@jwt_required()
@project_access_required
def export_project(project_id):
    p = db.session.get(Project, project_id)
    if not p:
        return jsonify(error="No such project."), 404
    payload = {
        "project": p.to_dict(),
        "team": [a.user.to_public_dict() for a in ProjectAccess.query.filter_by(project_id=project_id).all()],
        "tasks": [t.to_dict() for t in Task.query.filter_by(project_id=project_id).all()],
        "feedback": [m.to_dict() for m in Message.query.filter_by(project_id=project_id).all()],
        "siteUpdates": [{"id": x.id, "date": x.log_date.isoformat(), "title": x.title, "description": x.description, "progressPercent": x.progress_percent_snapshot, "transcript": x.audio_transcript, "photoCount": len(x.photos)} for x in ProgressLog.query.filter_by(project_id=project_id).all()],
        "files": [f.to_dict() for f in ProjectFile.query.filter_by(project_id=project_id).all()],
    }
    return current_app.response_class(json.dumps(payload, indent=2, default=str), mimetype="application/json",
                                      headers={"Content-Disposition": f'attachment; filename="{p.site_code}-backup.json"'})
