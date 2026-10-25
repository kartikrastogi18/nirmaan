import io

from app.models import Project, ProjectAccess, UserRole


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def setup_project(db, make_user):
    boss = make_user(UserRole.BOSS, "9000000101", "Boss")
    contractor = make_user(UserRole.CONTRACTOR, "9000000102", "Contractor")
    architect = make_user(UserRole.ARCHITECT, "9000000103", "Architect")
    outsider = make_user(UserRole.CLIENT, "9000000104", "Outsider")
    project = Project(site_code="M1", name="Media Site", created_by=boss)
    db.session.add(project); db.session.flush()
    db.session.add_all([
        ProjectAccess(user_id=contractor.id, project_id=project.id, granted_by_id=boss.id),
        ProjectAccess(user_id=architect.id, project_id=project.id, granted_by_id=boss.id),
    ])
    db.session.commit()
    return project, contractor, architect, outsider


def test_contractor_posts_photo_voice_and_transcript(client, db, make_user, token_for):
    project, contractor, _, _ = setup_project(db, make_user)
    response = client.post(
        f"/api/projects/{project.id}/progress",
        headers=auth(token_for(contractor)),
        data={
            "title": "Slab complete",
            "description": "Concrete pour finished.",
            "transcript": "The slab pour is complete.",
            "progressPercent": "42",
            "photos": (io.BytesIO(b"\xff\xd8\xff\xe0valid-jpeg"), "site.jpg"),
            "audio": (io.BytesIO(b"\x1a\x45\xdf\xa3valid-webm"), "note.webm"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    body = response.get_json()["update"]
    assert body["audioTranscript"] == "The slab pour is complete."
    assert body["progressPercentSnapshot"] == 42
    assert len(body["photos"]) == 1
    assert body["audioUrl"]


def test_architect_can_view_but_not_post(client, db, make_user, token_for):
    project, _, viewer, _ = setup_project(db, make_user)
    assert client.get(f"/api/projects/{project.id}/progress", headers=auth(token_for(viewer))).status_code == 200
    denied = client.post(f"/api/projects/{project.id}/progress", headers=auth(token_for(viewer)), data={"title": "No"})
    assert denied.status_code == 403


def test_outsider_cannot_view_progress(client, db, make_user, token_for):
    project, _, _, outsider = setup_project(db, make_user)
    response = client.get(f"/api/projects/{project.id}/progress", headers=auth(token_for(outsider)))
    assert response.status_code == 403


def test_rejects_disguised_non_image_upload(client, db, make_user, token_for):
    project, contractor, _, _ = setup_project(db, make_user)
    response = client.post(
        f"/api/projects/{project.id}/progress",
        headers=auth(token_for(contractor)),
        data={"title": "Bad upload", "photos": (io.BytesIO(b"not an image"), "site.jpg", "text/plain")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "Unsupported" in response.get_json()["error"]


def test_rejects_more_than_photo_limit(client, db, make_user, token_for):
    project, contractor, _, _ = setup_project(db, make_user)
    photos = [(io.BytesIO(b"\xff\xd8\xff\xe0valid-jpeg"), f"site-{i}.jpg", "image/jpeg") for i in range(13)]
    response = client.post(
        f"/api/projects/{project.id}/progress",
        headers=auth(token_for(contractor)),
        data={"title": "Too many", "photos": photos},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "up to 12 photos" in response.get_json()["error"]

def test_rejects_spoofed_jpeg_signature(client, db, make_user, token_for):
    project, contractor, _, _ = setup_project(db, make_user)
    response = client.post(
        f"/api/projects/{project.id}/progress",
        headers=auth(token_for(contractor)),
        data={"title": "Spoofed", "photos": (io.BytesIO(b"not-really-a-jpeg"), "site.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "valid supported image" in response.get_json()["error"]
