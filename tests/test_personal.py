import io
from app.models import Project, ProjectAccess, UserRole


def auth(token): return {"Authorization": f"Bearer {token}"}


def setup_project(db, make_user):
    boss = make_user(UserRole.BOSS, "9000000101", "Boss")
    client = make_user(UserRole.CLIENT, "9000000102", "Friend")
    p = Project(site_code="HOME1", name="Home Project", created_by=boss)
    db.session.add(p); db.session.flush()
    db.session.add(ProjectAccess(project_id=p.id, user_id=client.id, granted_by_id=boss.id))
    db.session.commit()
    return boss, client, p


def test_project_file_upload_list_download_and_export(client, db, make_user, token_for):
    boss, _friend, p = setup_project(db, make_user)
    h = auth(token_for(boss))
    rv = client.post(f"/api/projects/{p.id}/files", headers=h, data={"file": (io.BytesIO(b"hello"), "notes.txt")}, content_type="multipart/form-data")
    assert rv.status_code == 201
    file_id = rv.get_json()["file"]["id"]
    rv = client.get(f"/api/projects/{p.id}/files", headers=h)
    assert rv.status_code == 200 and len(rv.get_json()["files"]) == 1
    rv = client.get(f"/api/projects/{p.id}/files/{file_id}", headers=h)
    assert rv.status_code == 200 and rv.data == b"hello"
    rv = client.get(f"/api/projects/{p.id}/export", headers=h)
    assert rv.status_code == 200 and b'"Home Project"' in rv.data


def test_project_file_isolation(client, db, make_user, token_for):
    boss, friend, p = setup_project(db, make_user)
    other = Project(site_code="OTHER", name="Other", created_by=boss)
    db.session.add(other); db.session.commit()
    rv = client.get(f"/api/projects/{other.id}/files", headers=auth(token_for(friend)))
    assert rv.status_code == 403


def test_search_requires_access(client, db, make_user, token_for):
    boss, friend, p = setup_project(db, make_user)
    other = Project(site_code="OTHER2", name="Other", created_by=boss)
    db.session.add(other); db.session.commit()
    rv = client.get(f"/api/projects/{other.id}/search?q=task", headers=auth(token_for(friend)))
    assert rv.status_code == 403
