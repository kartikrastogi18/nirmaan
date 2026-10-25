from __future__ import annotations

import os
import io
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import current_user, jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import ProgressLog, ProgressPhoto, UserRole
from app.services.activity import notify_project, record
from app.services.access_control import project_access_required, require_project_access
from app.services import storage

progress_bp = Blueprint("progress", __name__)

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "heic"}
AUDIO_EXTENSIONS = {"webm", "ogg", "mp3", "m4a", "wav", "mp4"}


def _upload_root() -> Path:
    configured = current_app.config.get("UPLOAD_ROOT")
    root = Path(configured) if configured else Path(current_app.instance_path) / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _looks_like_image(file, ext: str) -> bool:
    head = file.stream.read(32)
    file.stream.seek(0)
    if ext in {"jpg", "jpeg"}: return head.startswith(b"\xff\xd8\xff")
    if ext == "png": return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == "webp": return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if ext == "heic": return len(head) >= 12 and head[4:8] == b"ftyp" and head[8:12] in {b"heic", b"heix", b"hevc", b"hevx", b"mif1"}
    return False



def _looks_like_audio(file, ext: str) -> bool:
    head = file.stream.read(32)
    file.stream.seek(0)
    if ext == "ogg": return head.startswith(b"OggS")
    if ext == "wav": return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    if ext == "webm": return head.startswith(b"\x1a\x45\xdf\xa3")
    if ext == "mp3": return head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)
    if ext in {"m4a", "mp4"}: return len(head) >= 12 and head[4:8] == b"ftyp"
    return False

def _save_upload(file, folder: str, allowed: set[str], allowed_mime_prefixes: tuple[str, ...]) -> str:
    original = secure_filename(file.filename or "")
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    mimetype = (file.mimetype or "").lower()
    if ext not in allowed or not any(mimetype.startswith(prefix) for prefix in allowed_mime_prefixes):
        raise ValueError(f"Unsupported {folder[:-1] if folder.endswith('s') else folder} file type.")
    if folder == "photos" and not _looks_like_image(file, ext):
        raise ValueError("The uploaded photo does not contain a valid supported image.")
    if folder == "audio" and not _looks_like_audio(file, ext):
        raise ValueError("The uploaded voice note does not contain valid supported audio.")
    stored = f"{uuid.uuid4().hex}.{ext}"
    key = f"{folder}/{stored}"
    storage.put_bytes(key, file.read(), file.mimetype)
    return key


def _media_url(path: str | None) -> str | None:
    return f"/api/progress/media/{path}" if path else None


def _log_dict(log: ProgressLog) -> dict:
    return {
        "id": log.id,
        "projectId": log.project_id,
        "author": log.author.to_public_dict(),
        "logDate": log.log_date.isoformat(),
        "title": log.title,
        "description": log.description,
        "progressPercentSnapshot": int(log.progress_percent_snapshot) if log.progress_percent_snapshot is not None else None,
        "audioUrl": _media_url(log.audio_note_path),
        "audioTranscript": log.audio_transcript,
        "photos": [
            {"id": p.id, "url": _media_url(p.file_path), "caption": p.caption, "latitude": p.latitude, "longitude": p.longitude, "accuracyM": p.accuracy_m, "capturedAt": p.captured_at.isoformat() if p.captured_at else None}
            for p in log.photos
        ],
        "createdAt": log.created_at.isoformat() if log.created_at else None,
    }


@progress_bp.get("/projects/<int:project_id>/progress")
@jwt_required()
@project_access_required
def list_progress(project_id):
    logs = (
        ProgressLog.query.filter_by(project_id=project_id)
        .order_by(ProgressLog.log_date.desc(), ProgressLog.id.desc())
        .all()
    )
    return jsonify(updates=[_log_dict(log) for log in logs])


@progress_bp.post("/projects/<int:project_id>/progress")
@jwt_required()
@project_access_required
def create_progress(project_id):
    if current_user.role not in {UserRole.CONTRACTOR, UserRole.PROJECT_MANAGER, UserRole.BOSS, UserRole.CLIENT}:
        return jsonify(error="Your role cannot post site updates."), 403

    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    transcript = (request.form.get("transcript") or "").strip()
    progress_percent = request.form.get("progressPercent")
    progress_val = None
    if progress_percent is not None and progress_percent != "":
        try:
            progress_val = float(progress_percent)
        except ValueError:
            pass

    if not title:
        return jsonify(error="title is required."), 400
    if len(title) > 200:
        return jsonify(error="title must be 200 characters or fewer."), 400
    if len(description) > 10000:
        return jsonify(error="description must be 10000 characters or fewer."), 400
    if len(transcript) > 20000:
        return jsonify(error="transcript must be 20000 characters or fewer."), 400

    try:
        log_date = date.fromisoformat(request.form.get("logDate") or date.today().isoformat())
        latitude = float(request.form["latitude"]) if request.form.get("latitude") else None
        longitude = float(request.form["longitude"]) if request.form.get("longitude") else None
        accuracy = float(request.form["accuracyM"]) if request.form.get("accuracyM") else None
        if latitude is not None and not -90 <= latitude <= 90: raise ValueError("latitude is invalid.")
        if longitude is not None and not -180 <= longitude <= 180: raise ValueError("longitude is invalid.")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    saved_paths: list[str] = []
    try:
        log = ProgressLog(
            project_id=project_id,
            author_id=current_user.id,
            log_date=log_date,
            title=title,
            description=description or None,
            progress_percent_snapshot=progress_val,
            audio_transcript=transcript or None,
        )
        db.session.add(log)
        db.session.flush()

        photos = [photo for photo in request.files.getlist("photos") if photo and photo.filename]
        if len(photos) > current_app.config.get("MAX_PHOTO_COUNT", 12):
            raise ValueError(f"You can attach up to {current_app.config.get('MAX_PHOTO_COUNT', 12)} photos per update.")
        for photo in photos:
            path = _save_upload(photo, "photos", IMAGE_EXTENSIONS, ("image/",))
            saved_paths.append(path)
            db.session.add(ProgressPhoto(log_id=log.id, file_path=path, latitude=latitude, longitude=longitude, accuracy_m=accuracy, captured_at=datetime.now(timezone.utc) if latitude is not None else None))

        audio = request.files.get("audio")
        if audio and audio.filename:
            path = _save_upload(audio, "audio", AUDIO_EXTENSIONS, ("audio/", "video/webm", "video/mp4"))
            saved_paths.append(path)
            log.audio_note_path = path

        record(current_user, project_id, "progress.post", f"Posted site update: {log.title}", "progress_log", log.id)
        notify_project(project_id, f"New site update: {log.title}", "site_update", exclude_user_id=current_user.id)
        db.session.commit()
        return jsonify(update=_log_dict(log)), 201
    except ValueError as exc:
        db.session.rollback()
        for rel in saved_paths:
            try:
                storage.delete(rel)
            except Exception:
                pass
        return jsonify(error=str(exc)), 400


@progress_bp.get("/progress/media/<path:filename>")
@jwt_required()
def get_progress_media(filename):
    # The filename is random and unguessable, but that is not authorization.
    # Resolve its owning log and re-check project access before serving bytes.
    photo = ProgressPhoto.query.filter_by(file_path=filename).first()
    log = photo.log if photo else ProgressLog.query.filter_by(audio_note_path=filename).first()
    if log is None:
        return jsonify(error="No such media file."), 404
    if not require_project_access(current_user, log.project_id):
        return jsonify(error="You don't have access to this project."), 403
    if not storage.exists(filename):
        return jsonify(error="Stored media file is missing."), 404
    response = send_file(io.BytesIO(storage.get_bytes(filename)), download_name=filename.rsplit("/", 1)[-1])
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
