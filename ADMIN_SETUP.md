# Nirmaan Software — Admin Setup

1. Deploy the repository to an HTTPS Python host.
2. Set strong SECRET_KEY and JWT_SECRET_KEY values in the host secret/environment UI.
3. Set DATABASE_URL to the shared PostgreSQL database.
4. For permanent media, set STORAGE_BACKEND=s3 plus S3 endpoint, region, bucket, access key and secret.
5. Keep the media bucket private; Nirmaan serves authorized media through its backend.
6. Open /api/live and /api/health after deployment. Health must report ready before inviting users.
7. Create/seed the first Boss account using the documented initialization path, then approve friend accounts from the app.
8. Test Boss and Contractor on two separate devices before relying on the app.
9. Keep provider-level PostgreSQL/media backups enabled. `backup_personal.py` is for local SQLite Personal Edition backups, not managed PostgreSQL.
