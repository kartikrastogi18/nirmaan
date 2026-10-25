# Publish TotalWorks on Render

1. Create a GitHub repository and upload the **contents of this folder** (so `render.yaml` is at repository root). Keep the repo private if your code is confidential.
2. Open https://dashboard.render.com/ and select **New > Blueprint**. Connect your GitHub repository.
3. Review the resources and pricing before applying: this Blueprint requests a **paid Starter web service, 1 GB persistent disk, and paid PostgreSQL database**.
4. Apply the Blueprint and wait for a successful deploy. Render will show your public URL, typically `https://totalworks-site.onrender.com` (the actual name may differ).
5. Visit `/api/health` at your URL to confirm the database is healthy, then open `/` for the site. Register an account and test photo/audio uploads.

## Notes
- The app serves its frontend and backend from the same web service. No separate frontend deployment is needed.
- Uploaded media lives under `/var/data/instance/uploads`, on Render's persistent disk. Without a disk, uploaded files can disappear during restarts/deploys.
- PostgreSQL holds users, projects and updates. The startup script creates missing tables on a fresh database; future schema changes need proper migrations.
- Do not commit `.env` or credentials. Render generates Flask/JWT secrets automatically.
- HTTPS is provided by Render. Browser camera and microphone permissions require HTTPS or localhost.
- For any production use, run the full test suite and perform a security review before inviting real users.
