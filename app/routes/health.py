from flask import Blueprint, jsonify
from app.extensions import db
from app.services import storage

health_bp = Blueprint("health", __name__)

@health_bp.get("/live")
def live():
    return jsonify(status="alive"), 200

@health_bp.get("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1")); db_ok = True
    except Exception:
        db_ok = False
    try:
        storage.check_writable(); storage_ok = True
    except Exception:
        storage_ok = False
    ready = db_ok and storage_ok
    return jsonify(status="healthy" if ready else "degraded", database=db_ok, storage=storage_ok, storageBackend=storage.backend()), (200 if ready else 503)
