# Nirmaan Software v1.1 workflow pass

Implemented before deployment:
- Optional geotag metadata (latitude, longitude, accuracy, capture time) on progress photos.
- Clear location permission fallback; camera/microphone secure-context flows retained.
- Login tokens persist across browser restarts via localStorage; expired access tokens can refresh using the stored refresh token.
- Role-oriented workspace copy and reduced irrelevant panels for Contractor/Client.
- Client role may post site/photo updates while backend project access remains mandatory.
- Manual overall-progress field removed from site updates and direct project overall-progress edits rejected.
- Overall project progress is recalculated from the arithmetic mean of project task progress after task create/update/delete.
- Budget/spent edits are Boss/Admin-only at the API layer; Boss UI has an explicit financial editor.
- Tasks support deadline date plus optional HH:MM time.
- Task UI groups work into Overdue, Today, Upcoming and Completed.
- Feedback messages and site updates display timestamps; models already store created_at/updated_at timestamps.
- Added regression tests covering Boss-only finance, client geotag photo posts, automatic project progress, deadline time, and rejection of manual overall progress.

Verification in this build:
- `python -m compileall app tests`: PASS
- `node --check app/static/js/app.js`: PASS
- `node --check app/static/js/api.js`: PASS
- `python verify_release.py`: PASS
- Full `pytest`: NOT RUN because this runtime lacks flask_jwt_extended. Run `pip install -r requirements.txt && pytest -q` in CI/deployment.

Database note:
The new fields are intended for the new Neon database before first production launch. If upgrading an already-populated database later, use a schema migration for `tasks.due_time` and the new `progress_photos` geotag columns.
