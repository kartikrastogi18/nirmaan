# Nirmaan Internet Sync Setup

## What is already implemented
- One server API is the source of truth for users, projects, tasks, updates, feedback, notifications and activity.
- PostgreSQL is supported through `DATABASE_URL`.
- Private S3-compatible storage is supported for site photos, voice notes and project files.
- Logged-in browsers auto-refresh shared project data every 15 seconds.
- The header shows Online / Syncing / Offline.
- After reconnecting, Nirmaan immediately refreshes from the server.
- Media downloads are authorized by Nirmaan before bytes are returned.

## Free/personal deployment pattern
1. Private GitHub repository containing this project.
2. A free PostgreSQL provider (for example Neon, subject to its current free-plan limits).
3. An S3-compatible object store (for example Cloudflare R2, subject to its current free-plan limits/setup requirements).
4. A Python web host with HTTPS (the included `render.yaml` is free-tier friendly where Render's current plan permits it).

Provider plans change, so confirm current pricing before creating resources.

## Proof-of-sync test after deployment
1. Phone A logs in as Boss.
2. Phone B logs in as Contractor/PM with access to the same project.
3. Phone A creates or changes a task.
4. Within 15 seconds Phone B should receive the server state without a page refresh.
5. Phone B posts a site update with a photo/voice note.
6. Within 15 seconds Phone A should see the update; protected media should open only for authorized project members.
7. Turn off Wi-Fi/mobile data on one device: header should show Offline and writes must not be reported as saved.
8. Restore internet: header returns Online and the app refreshes from the server.
