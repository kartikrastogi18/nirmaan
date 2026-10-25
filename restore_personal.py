"""Restore a Nirmaan Personal Edition LOCAL backup. Refuses remote DB/storage restores."""
from __future__ import annotations
import argparse, os, shutil, sqlite3, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser(); ap.add_argument('backup'); ap.add_argument('--yes',action='store_true'); args=ap.parse_args()
if os.environ.get('DATABASE_URL','').strip(): raise SystemExit('Refusing restore while DATABASE_URL is set. Restore managed PostgreSQL using provider tooling.')
if os.environ.get('STORAGE_BACKEND','local') != 'local': raise SystemExit('Refusing restore for non-local media storage. Use provider recovery tooling.')
if not args.yes: raise SystemExit('Re-run with --yes after stopping Nirmaan and confirming you want to replace local data.')
instance=Path(os.environ.get('INSTANCE_PATH',ROOT/'instance')); uploads=Path(os.environ.get('UPLOAD_ROOT',instance/'uploads')); db=instance/'totalworks.db'; instance.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as td:
    with zipfile.ZipFile(args.backup) as z: z.extractall(td)
    snap=Path(td)/'database/totalworks.db'
    if snap.exists():
        # Verify snapshot is readable before replacement.
        c=sqlite3.connect(snap); ok=c.execute('PRAGMA integrity_check').fetchone()[0]; c.close()
        if ok!='ok': raise SystemExit(f'Backup database failed integrity check: {ok}')
        shutil.copy2(snap,db)
    src=Path(td)/'uploads'
    if src.exists():
        if uploads.exists(): shutil.rmtree(uploads)
        shutil.copytree(src,uploads)
print('Restore completed successfully.')
