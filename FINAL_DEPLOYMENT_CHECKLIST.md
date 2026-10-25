# Nirmaan Software — Final Deployment Checklist

## Code (prepared)
- [x] Server-backed shared data model
- [x] 15-second automatic refresh and reconnect sync
- [x] Online / Syncing / Offline indicator
- [x] PWA manifest, service worker, icons and install action
- [x] Nirmaan Software production branding
- [x] PostgreSQL-ready configuration
- [x] S3-compatible private media configuration
- [x] HTTPS/security headers and production secret validation
- [x] Backup utility and guarded local restore utility
- [x] Regression/release checks
- [x] User and admin guides

## Owner/account actions
- [ ] Put this source in a private GitHub repository
- [ ] Create shared PostgreSQL and copy DATABASE_URL into host secrets
- [ ] Create private S3-compatible media bucket and add its credentials to host secrets
- [ ] Authorize hosting provider to deploy the GitHub repository
- [ ] Confirm /api/live and /api/health are healthy on HTTPS
- [ ] Create first Boss/Admin account
- [ ] Approve friend accounts and grant project access

## Real-device acceptance
- [ ] Boss creates task on Phone A; Contractor sees it on Phone B
- [ ] Contractor posts progress; Boss receives it after sync
- [ ] Photo upload and camera capture work over HTTPS
- [ ] Voice recording/playback works over HTTPS
- [ ] Speech-to-text tested on intended browser (browser-dependent)
- [ ] Files and notifications visible to correct roles
- [ ] Offline indicator and reconnect refresh verified
- [ ] Backup/recovery procedure verified with hosting providers

## Final sharing
- [ ] Insert live HTTPS URL into share sheet
- [ ] Generate QR code
- [ ] Share final PDF/user guide with friends
