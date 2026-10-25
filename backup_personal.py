"""Create a consistent Personal Edition backup (SQLite DB + uploads + metadata)."""
from __future__ import annotations
import json, os, sqlite3, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent
instance = Path(os.environ.get("INSTANCE_PATH", root / "instance"))
uploads = Path(os.environ.get("UPLOAD_ROOT", instance / "uploads"))
out_dir = root / "backups"; out_dir.mkdir(exist_ok=True)
stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
out = out_dir / f"nirmaan-backup-{stamp}.zip"
db = instance / "totalworks.db"

with tempfile.TemporaryDirectory() as td:
    snapshot = Path(td) / "totalworks.db"
    if db.exists():
        # SQLite may be in WAL mode while the app is running. Copying only the
        # .db file can therefore produce an incomplete backup. The online
        # backup API creates a transactionally consistent snapshot.
        src = sqlite3.connect(db)
        dst = sqlite3.connect(snapshot)
        try:
            src.backup(dst)
        finally:
            dst.close(); src.close()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        if snapshot.exists(): z.write(snapshot, "database/totalworks.db")
        if uploads.exists():
            for p in uploads.rglob("*"):
                if p.is_file(): z.write(p, Path("uploads") / p.relative_to(uploads))
        z.writestr("backup.json", json.dumps({"createdAt": datetime.now(timezone.utc).isoformat(), "app": "Nirmaan Personal Edition"}, indent=2))
print(out)
