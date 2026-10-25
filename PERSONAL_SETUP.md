# Nirmaan Personal Edition

This build is optimized for a small trusted group (you + friends), while retaining server-side role authorization, HTTPS-ready security headers, protected media, validation and project isolation.

## Run locally

1. Create a virtual environment: `python3 -m venv .venv`
2. Activate it: `source .venv/bin/activate` (Windows: `.venv\\Scripts\\activate`)
3. Install: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and generate strong secrets.
5. Initialize: `python init_db.py`
6. Run: `python run.py`
7. Open `http://localhost:5000`.

`localhost` is considered a secure context by modern browsers for camera/microphone APIs. For phones/friends over the internet, deploy behind HTTPS.

## Personal Edition features

- Private accounts with Boss/Admin approval
- Boss, Project Manager, Architect, Contractor and Client roles
- Project/team isolation and access control
- Tasks, deadlines, status and progress
- Project progress/budget/spend overview
- Site updates with multiple photos, live camera, voice note and editable speech transcript
- Feedback/discussion
- Project file uploads/downloads (15 MB per file)
- Project search across tasks, feedback, site updates and files
- Activity trail
- In-app notifications
- Per-project JSON export/backup
- Local full backup helper: `python backup_personal.py`
- Responsive phone/tablet/desktop UI

## Internet deployment

External hosting authorization is the only unavoidable user-owned step. Use a Python HTTPS host plus PostgreSQL and persistent media storage. Do not put secrets in Git or chat; set them as host environment variables.

For a tiny private group, `RATELIMIT_STORAGE_URI=memory://` is acceptable on a single worker. Redis is optional unless you scale to multiple workers.
