from app.models import Message, Project, ProjectAccess, UserRole


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _make_project(db, boss, code="A", name="Skyline Residency"):
    project = Project(site_code=code, name=name, created_by=boss)
    db.session.add(project)
    db.session.commit()
    return project


def _grant(db, user, project, boss):
    db.session.add(ProjectAccess(user_id=user.id, project_id=project.id, granted_by_id=boss.id))
    db.session.commit()


class TestListMessages:
    def test_requires_project_access(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9400000001")
        outsider = make_user(UserRole.CONTRACTOR, "9400000002")
        site = _make_project(db, boss, "A")

        resp = client.get(f"/api/projects/{site.id}/messages", headers=_auth_header(token_for(outsider)))
        assert resp.status_code == 403

    def test_returned_oldest_first(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9400000003")
        site = _make_project(db, boss, "A")
        db.session.add_all(
            [
                Message(project_id=site.id, sender=boss, body="First"),
                Message(project_id=site.id, sender=boss, body="Second"),
            ]
        )
        db.session.commit()

        resp = client.get(f"/api/projects/{site.id}/messages", headers=_auth_header(token_for(boss)))
        bodies = [m["body"] for m in resp.get_json()["messages"]]
        assert bodies == ["First", "Second"]


class TestPostMessage:
    def test_any_project_member_can_post_including_client(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9400000010")
        orion = make_user(UserRole.CLIENT, "9400000011", name="Orion Realty")
        site = _make_project(db, boss, "A")
        _grant(db, orion, site, boss)

        resp = client.post(
            f"/api/projects/{site.id}/messages",
            json={"body": "The lobby tile colour doesn't match what we agreed."},
            headers=_auth_header(token_for(orion)),
        )
        assert resp.status_code == 201
        body = resp.get_json()["message"]
        assert body["sender"]["role"] == "client"
        assert "lobby tile" in body["body"]

    def test_outsider_cannot_post(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9400000012")
        outsider = make_user(UserRole.CONTRACTOR, "9400000013")
        site = _make_project(db, boss, "A")

        resp = client.post(
            f"/api/projects/{site.id}/messages",
            json={"body": "Hello"},
            headers=_auth_header(token_for(outsider)),
        )
        assert resp.status_code == 403

    def test_empty_body_is_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9400000014")
        site = _make_project(db, boss, "A")
        resp = client.post(
            f"/api/projects/{site.id}/messages",
            json={"body": "   "},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 400

    def test_overlong_body_is_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9400000015")
        site = _make_project(db, boss, "A")
        resp = client.post(
            f"/api/projects/{site.id}/messages",
            json={"body": "x" * 2001},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 400

    def test_missing_json_body_is_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9400000016")
        site = _make_project(db, boss, "A")
        resp = client.post(
            f"/api/projects/{site.id}/messages",
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 400
