import io

from app.extensions import db
from app.models import (Drawing, DrawingCategory, DrawingRevision, Project,
                        ProjectAccess, RevisionStatus, UserRole, UserStatus)


def headers(token_for, user):
    return {"Authorization": f"Bearer {token_for(user)}"}


def make_project(boss, code="AUD"):
    p = Project(site_code=code, name="Audit project", created_by=boss)
    db.session.add(p); db.session.commit(); return p


def grant(user, project, boss):
    db.session.add(ProjectAccess(user_id=user.id, project_id=project.id, granted_by_id=boss.id)); db.session.commit()


def test_client_cannot_upload_project_file(client, make_user, token_for):
    boss = make_user(UserRole.BOSS, "10000001", "Boss")
    user = make_user(UserRole.CLIENT, "10000002", "Client")
    project = make_project(boss); grant(user, project, boss)
    r = client.post(f"/api/projects/{project.id}/files", data={"file": (io.BytesIO(b"hello"), "note.txt")}, headers=headers(token_for, user))
    assert r.status_code == 403


def test_project_rejects_non_finite_budget(client, make_user, token_for):
    boss = make_user(UserRole.BOSS, "10000003", "Boss")
    r = client.post("/api/projects", json={"siteCode":"NF","name":"Bad","budget":"NaN"}, headers=headers(token_for, boss))
    assert r.status_code == 400


def test_search_rejects_excessive_query(client, make_user, token_for):
    boss = make_user(UserRole.BOSS, "10000004", "Boss")
    user = make_user(UserRole.CONTRACTOR, "10000005", "Contractor")
    project = make_project(boss); grant(user, project, boss)
    r = client.get(f"/api/projects/{project.id}/search?q=" + "x"*201, headers=headers(token_for, user))
    assert r.status_code == 400


def test_suspended_user_existing_token_is_rejected(client, make_user, token_for):
    user = make_user(UserRole.CONTRACTOR, "10000006", "Contractor")
    auth = headers(token_for, user)
    user.status = UserStatus.SUSPENDED; db.session.commit()
    r = client.get("/api/auth/me", headers=auth)
    assert r.status_code == 401


def test_client_sees_only_approved_drawings(client, make_user, token_for):
    boss = make_user(UserRole.BOSS, "10000007", "Boss")
    user = make_user(UserRole.CLIENT, "10000008", "Client")
    project = make_project(boss); grant(user, project, boss)
    d = Drawing(project_id=project.id, name="Plan", category=DrawingCategory.ARCHITECTURAL, uploaded_by=boss)
    db.session.add(d); db.session.flush()
    db.session.add(DrawingRevision(drawing_id=d.id, version_label="Rev 1", file_path="pending.pdf", uploaded_by=boss))
    db.session.add(DrawingRevision(drawing_id=d.id, version_label="Rev 0", file_path="approved.pdf", uploaded_by=boss, status=RevisionStatus.APPROVED))
    db.session.commit()
    r = client.get(f"/api/projects/{project.id}/drawings", headers=headers(token_for, user))
    payload = r.get_json()["drawings"]
    assert r.status_code == 200 and len(payload) == 1
    assert payload[0]["latestRevision"]["status"] == RevisionStatus.APPROVED.value


def test_fake_audio_rejected(client, make_user, token_for):
    boss = make_user(UserRole.BOSS, "10000009", "Boss")
    user = make_user(UserRole.CONTRACTOR, "10000010", "Contractor")
    project = make_project(boss); grant(user, project, boss)
    data = {"title":"Update", "audio": (io.BytesIO(b"not audio"), "voice.webm")}
    r = client.post(f"/api/projects/{project.id}/progress", data=data, headers=headers(token_for, user), content_type="multipart/form-data")
    assert r.status_code == 400
