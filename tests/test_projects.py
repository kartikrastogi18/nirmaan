from app.models import Project, ProjectAccess, UserRole


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _make_project(db, boss, code="A", name="Skyline Residency", budget=1000000):
    project = Project(site_code=code, name=name, created_by=boss, budget=budget)
    db.session.add(project)
    db.session.commit()
    return project


class TestListProjects:
    def test_boss_sees_every_project(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000001")
        _make_project(db, boss, "A", "Skyline Residency")
        _make_project(db, boss, "B", "Green Valley")

        resp = client.get("/api/projects", headers=_auth_header(token_for(boss)))
        assert resp.status_code == 200
        assert len(resp.get_json()["projects"]) == 2

    def test_contractor_sees_only_their_assigned_site(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000002")
        contractor = make_user(UserRole.CONTRACTOR, "9000000003")
        site_a = _make_project(db, boss, "A", "Skyline Residency")
        _make_project(db, boss, "B", "Green Valley")
        db.session.add(
            ProjectAccess(user_id=contractor.id, project_id=site_a.id, granted_by_id=boss.id)
        )
        db.session.commit()

        resp = client.get("/api/projects", headers=_auth_header(token_for(contractor)))
        projects = resp.get_json()["projects"]
        assert len(projects) == 1
        assert projects[0]["siteCode"] == "A"

    def test_requires_authentication(self, client):
        assert client.get("/api/projects").status_code == 401


class TestCreateProject:
    def test_boss_can_create_a_project(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000010")
        resp = client.post(
            "/api/projects",
            json={"siteCode": "A", "name": "Skyline Residency", "budget": 45000000},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 201
        assert resp.get_json()["project"]["siteCode"] == "A"
        assert resp.get_json()["project"]["budget"] == 45000000

    def test_non_boss_cannot_create_a_project(self, client, db, make_user, token_for):
        pm = make_user(UserRole.PROJECT_MANAGER, "9000000011")
        resp = client.post(
            "/api/projects",
            json={"siteCode": "A", "name": "Skyline Residency"},
            headers=_auth_header(token_for(pm)),
        )
        assert resp.status_code == 403

    def test_duplicate_site_code_falls_through_to_409(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000012")
        token = token_for(boss)
        client.post(
            "/api/projects", json={"siteCode": "A", "name": "First"}, headers=_auth_header(token)
        )
        resp = client.post(
            "/api/projects", json={"siteCode": "A", "name": "Second"}, headers=_auth_header(token)
        )
        assert resp.status_code == 409

    def test_missing_name_is_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000013")
        resp = client.post(
            "/api/projects", json={"siteCode": "A"}, headers=_auth_header(token_for(boss))
        )
        assert resp.status_code == 400


class TestGetProject:
    def test_assigned_user_can_view_it(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000020")
        architect = make_user(UserRole.ARCHITECT, "9000000021")
        site = _make_project(db, boss, "A")
        db.session.add(
            ProjectAccess(user_id=architect.id, project_id=site.id, granted_by_id=boss.id)
        )
        db.session.commit()

        resp = client.get(f"/api/projects/{site.id}", headers=_auth_header(token_for(architect)))
        assert resp.status_code == 200
        assert resp.get_json()["project"]["name"] == "Skyline Residency"

    def test_unassigned_user_gets_403_not_404(self, client, db, make_user, token_for):
        # 403, not 404 -- see project_access_required's docstring: a user
        # with no grant shouldn't be able to tell "not yours" from
        # "doesn't exist" via the status code either.
        boss = make_user(UserRole.BOSS, "9000000022")
        outsider = make_user(UserRole.CONTRACTOR, "9000000023")
        site = _make_project(db, boss, "A")

        resp = client.get(f"/api/projects/{site.id}", headers=_auth_header(token_for(outsider)))
        assert resp.status_code == 403


class TestUpdateProject:
    def test_assigned_pm_can_update_it(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000030")
        pm = make_user(UserRole.PROJECT_MANAGER, "9000000031")
        site = _make_project(db, boss, "A")
        db.session.add(ProjectAccess(user_id=pm.id, project_id=site.id, granted_by_id=boss.id))
        db.session.commit()

        resp = client.patch(
            f"/api/projects/{site.id}",
            json={"status": "delayed"},
            headers=_auth_header(token_for(pm)),
        )
        assert resp.status_code == 200
        body = resp.get_json()["project"]
        assert body["status"] == "delayed"

    def test_assigned_contractor_still_cannot_update_wrong_role(
        self, client, db, make_user, token_for
    ):
        # Has project access but the wrong role -- proves the two gates are
        # independent; access alone isn't enough.
        boss = make_user(UserRole.BOSS, "9000000032")
        contractor = make_user(UserRole.CONTRACTOR, "9000000033")
        site = _make_project(db, boss, "A")
        db.session.add(
            ProjectAccess(user_id=contractor.id, project_id=site.id, granted_by_id=boss.id)
        )
        db.session.commit()

        resp = client.patch(
            f"/api/projects/{site.id}",
            json={"status": "delayed"},
            headers=_auth_header(token_for(contractor)),
        )
        assert resp.status_code == 403

    def test_unassigned_pm_still_cannot_update_no_access(self, client, db, make_user, token_for):
        # Right role but no grant for this site -- the other half of the
        # same proof.
        boss = make_user(UserRole.BOSS, "9000000034")
        pm = make_user(UserRole.PROJECT_MANAGER, "9000000035")
        site = _make_project(db, boss, "A")

        resp = client.patch(
            f"/api/projects/{site.id}",
            json={"status": "delayed"},
            headers=_auth_header(token_for(pm)),
        )
        assert resp.status_code == 403

    def test_invalid_status_value_is_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000036")
        site = _make_project(db, boss, "A")
        resp = client.patch(
            f"/api/projects/{site.id}",
            json={"status": "on_fire"},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 400


class TestAccessGrants:
    def test_boss_can_grant_access(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000040")
        client_user = make_user(UserRole.CLIENT, "9000000041")
        site = _make_project(db, boss, "A")

        resp = client.post(
            f"/api/projects/{site.id}/access",
            json={"userId": client_user.public_id},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 201
        assert (
            ProjectAccess.query.filter_by(user_id=client_user.id, project_id=site.id).count() == 1
        )

    def test_non_manager_cannot_grant_access(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000042")
        contractor = make_user(UserRole.CONTRACTOR, "9000000043")
        target = make_user(UserRole.CLIENT, "9000000044")
        site = _make_project(db, boss, "A")
        db.session.add(ProjectAccess(user_id=contractor.id, project_id=site.id, granted_by_id=boss.id))
        db.session.commit()

        resp = client.post(
            f"/api/projects/{site.id}/access",
            json={"userId": target.public_id},
            headers=_auth_header(token_for(contractor)),
        )
        assert resp.status_code == 403

    def test_project_manager_can_grant_access_on_assigned_project(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000142")
        pm = make_user(UserRole.PROJECT_MANAGER, "9000000143")
        target = make_user(UserRole.CLIENT, "9000000144")
        site = _make_project(db, boss, "PM")
        db.session.add(ProjectAccess(user_id=pm.id, project_id=site.id, granted_by_id=boss.id))
        db.session.commit()

        resp = client.post(
            f"/api/projects/{site.id}/access",
            json={"userId": target.public_id},
            headers=_auth_header(token_for(pm)),
        )
        assert resp.status_code == 201
        assert ProjectAccess.query.filter_by(user_id=target.id, project_id=site.id).count() == 1

    def test_granting_access_twice_gives_a_clear_message_not_a_500(
        self, client, db, make_user, token_for
    ):
        boss = make_user(UserRole.BOSS, "9000000045")
        target = make_user(UserRole.CLIENT, "9000000046")
        site = _make_project(db, boss, "A")
        token = token_for(boss)

        client.post(
            f"/api/projects/{site.id}/access",
            json={"userId": target.public_id},
            headers=_auth_header(token),
        )
        resp = client.post(
            f"/api/projects/{site.id}/access",
            json={"userId": target.public_id},
            headers=_auth_header(token),
        )
        assert resp.status_code == 400
        assert "already has access" in resp.get_json()["error"]

    def test_revoking_access_removes_the_grant(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000047")
        target = make_user(UserRole.CLIENT, "9000000048")
        site = _make_project(db, boss, "A")
        token = token_for(boss)
        client.post(
            f"/api/projects/{site.id}/access",
            json={"userId": target.public_id},
            headers=_auth_header(token),
        )

        resp = client.delete(
            f"/api/projects/{site.id}/access/{target.public_id}", headers=_auth_header(token)
        )
        assert resp.status_code == 200
        assert ProjectAccess.query.filter_by(user_id=target.id, project_id=site.id).count() == 0

    def test_team_endpoint_lists_everyone_with_a_grant(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000049")
        pm = make_user(UserRole.PROJECT_MANAGER, "9000000050")
        site = _make_project(db, boss, "A")
        db.session.add(ProjectAccess(user_id=pm.id, project_id=site.id, granted_by_id=boss.id))
        db.session.commit()

        resp = client.get(f"/api/projects/{site.id}/team", headers=_auth_header(token_for(pm)))
        assert resp.status_code == 200
        assert pm.name in [u["name"] for u in resp.get_json()["team"]]


class TestProjectValidationHardening:
    def test_negative_budget_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000991")
        resp = client.post("/api/projects", json={"siteCode":"NEG","name":"Bad","budget":-1}, headers=_auth_header(token_for(boss)))
        assert resp.status_code == 400

    def test_progress_over_100_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9000000992")
        site = _make_project(db, boss, "VAL")
        resp = client.patch(f"/api/projects/{site.id}", json={"progressPercent":101}, headers=_auth_header(token_for(boss)))
        assert resp.status_code == 400
