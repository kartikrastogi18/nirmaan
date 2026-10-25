# Nirmaan pre-deployment checklist

## Already implemented in code
- Production PostgreSQL configuration
- Persistent upload-path configuration
- Strong-secret startup validation
- JWT auth and role/project authorization
- Login/register/refresh rate-limit hooks
- Security headers, CSP, HSTS in production
- Protected project media
- File type + image signature validation
- Liveness and readiness endpoints
- Responsive role-aware frontend
- Camera, photo, voice-note and browser speech-to-text flows
- Automated backend test source

## Requires your account/action
- [ ] Connect GitHub repository to Render
- [ ] Create PostgreSQL service (Blueprint can do this)
- [ ] Create Redis/Key Value and set `RATELIMIT_STORAGE_URI`
- [ ] Confirm persistent disk or choose object storage
- [ ] Configure backups and retention
- [ ] Add uptime/error monitoring
- [ ] Deploy to HTTPS
- [ ] Test camera/microphone on iPhone/Android/Desktop
- [ ] Add email provider if password reset/email verification is wanted
- [ ] Add server transcription provider if universal transcription is wanted
- [ ] Run `pytest -q` in CI/deployment environment
