from app.models import Project, ProjectAccess, Task, TaskStatus, UserRole


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


class TestListTasks:
    def test_only_returns_tasks_for_this_project(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000001")
        site_a = _make_project(db, boss, "A")
        site_b = _make_project(db, boss, "B")
        db.session.add_all(
            [
                Task(project_id=site_a.id, title="Task A1", created_by=boss),
                Task(project_id=site_b.id, title="Task B1", created_by=boss),
            ]
        )
        db.session.commit()

        resp = client.get(
            f"/api/projects/{site_a.id}/tasks", headers=_auth_header(token_for(boss))
        )
        assert [t["title"] for t in resp.get_json()["tasks"]] == ["Task A1"]

    def test_requires_project_access(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000002")
        outsider = make_user(UserRole.CONTRACTOR, "9100000003")
        site = _make_project(db, boss, "A")

        resp = client.get(
            f"/api/projects/{site.id}/tasks", headers=_auth_header(token_for(outsider))
        )
        assert resp.status_code == 403

    def test_filters_by_status(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000004")
        site = _make_project(db, boss, "A")
        db.session.add_all(
            [
                Task(project_id=site.id, title="Done one", created_by=boss, status=TaskStatus.DONE),
                Task(project_id=site.id, title="Pending one", created_by=boss),
            ]
        )
        db.session.commit()

        resp = client.get(
            f"/api/projects/{site.id}/tasks?status=done", headers=_auth_header(token_for(boss))
        )
        assert [t["title"] for t in resp.get_json()["tasks"]] == ["Done one"]

    def test_filters_to_only_my_tasks(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000005")
        contractor = make_user(UserRole.CONTRACTOR, "9100000006")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)
        db.session.add_all(
            [
                Task(project_id=site.id, title="Mine", created_by=boss, assignee=contractor),
                Task(project_id=site.id, title="Not mine", created_by=boss),
            ]
        )
        db.session.commit()

        resp = client.get(
            f"/api/projects/{site.id}/tasks?mine=true",
            headers=_auth_header(token_for(contractor)),
        )
        assert [t["title"] for t in resp.get_json()["tasks"]] == ["Mine"]


class TestCreateTask:
    def test_pm_can_create_a_task(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000010")
        pm = make_user(UserRole.PROJECT_MANAGER, "9100000011")
        site = _make_project(db, boss, "A")
        _grant(db, pm, site, boss)

        resp = client.post(
            f"/api/projects/{site.id}/tasks",
            json={"title": "Cast 4th floor slab"},
            headers=_auth_header(token_for(pm)),
        )
        assert resp.status_code == 201
        body = resp.get_json()["task"]
        assert body["title"] == "Cast 4th floor slab"
        assert body["status"] == "pending"

    def test_contractor_cannot_create_a_task(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000012")
        contractor = make_user(UserRole.CONTRACTOR, "9100000013")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)

        resp = client.post(
            f"/api/projects/{site.id}/tasks",
            json={"title": "Sneaky task"},
            headers=_auth_header(token_for(contractor)),
        )
        assert resp.status_code == 403

    def test_cannot_assign_to_someone_without_access_to_this_site(
        self, client, db, make_user, token_for
    ):
        boss = make_user(UserRole.BOSS, "9100000014")
        outsider = make_user(UserRole.CONTRACTOR, "9100000015")  # no grant for site A
        site = _make_project(db, boss, "A")

        resp = client.post(
            f"/api/projects/{site.id}/tasks",
            json={"title": "Task", "assigneeId": outsider.public_id},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 400
        assert "doesn't have access" in resp.get_json()["error"]

    def test_can_assign_to_someone_who_has_access(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000016")
        contractor = make_user(UserRole.CONTRACTOR, "9100000017")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)

        resp = client.post(
            f"/api/projects/{site.id}/tasks",
            json={"title": "Task", "assigneeId": contractor.public_id},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 201
        assert resp.get_json()["task"]["assignee"]["id"] == contractor.public_id

    def test_missing_title_is_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000018")
        site = _make_project(db, boss, "A")
        resp = client.post(
            f"/api/projects/{site.id}/tasks", json={}, headers=_auth_header(token_for(boss))
        )
        assert resp.status_code == 400


class TestUpdateTask:
    def test_pm_can_edit_any_field(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000020")
        pm = make_user(UserRole.PROJECT_MANAGER, "9100000021")
        site = _make_project(db, boss, "A")
        _grant(db, pm, site, boss)
        task = Task(project_id=site.id, title="Original", created_by=boss)
        db.session.add(task)
        db.session.commit()

        resp = client.patch(
            f"/api/projects/{site.id}/tasks/{task.id}",
            json={"title": "Renamed", "priority": "high"},
            headers=_auth_header(token_for(pm)),
        )
        assert resp.status_code == 200
        body = resp.get_json()["task"]
        assert body["title"] == "Renamed"
        assert body["priority"] == "high"

    def test_assignee_can_update_status_and_progress_on_their_own_task(
        self, client, db, make_user, token_for
    ):
        boss = make_user(UserRole.BOSS, "9100000022")
        contractor = make_user(UserRole.CONTRACTOR, "9100000023")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)
        task = Task(project_id=site.id, title="Cast slab", created_by=boss, assignee=contractor)
        db.session.add(task)
        db.session.commit()

        resp = client.patch(
            f"/api/projects/{site.id}/tasks/{task.id}",
            json={"status": "in_progress", "progressPercent": 60},
            headers=_auth_header(token_for(contractor)),
        )
        assert resp.status_code == 200
        body = resp.get_json()["task"]
        assert body["status"] == "in_progress"
        assert body["progressPercent"] == 60

    def test_assignee_cannot_rename_their_own_task(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000024")
        contractor = make_user(UserRole.CONTRACTOR, "9100000025")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)
        task = Task(project_id=site.id, title="Cast slab", created_by=boss, assignee=contractor)
        db.session.add(task)
        db.session.commit()

        resp = client.patch(
            f"/api/projects/{site.id}/tasks/{task.id}",
            json={"title": "Renamed by contractor"},
            headers=_auth_header(token_for(contractor)),
        )
        assert resp.status_code == 400
        assert resp.get_json()["disallowedFields"] == ["title"]

    def test_someone_with_project_access_but_not_the_assignee_is_refused(
        self, client, db, make_user, token_for
    ):
        # Has project access (so it's not an isolation failure) but is
        # neither a manager nor this task's assignee.
        boss = make_user(UserRole.BOSS, "9100000026")
        contractor = make_user(UserRole.CONTRACTOR, "9100000027")
        bystander = make_user(UserRole.ARCHITECT, "9100000028")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)
        _grant(db, bystander, site, boss)
        task = Task(project_id=site.id, title="Cast slab", created_by=boss, assignee=contractor)
        db.session.add(task)
        db.session.commit()

        resp = client.patch(
            f"/api/projects/{site.id}/tasks/{task.id}",
            json={"status": "done"},
            headers=_auth_header(token_for(bystander)),
        )
        assert resp.status_code == 403

    def test_progress_percent_out_of_range_is_rejected(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000029")
        site = _make_project(db, boss, "A")
        task = Task(project_id=site.id, title="Task", created_by=boss)
        db.session.add(task)
        db.session.commit()

        resp = client.patch(
            f"/api/projects/{site.id}/tasks/{task.id}",
            json={"progressPercent": 150},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 400

    def test_boolean_is_not_accepted_as_a_progress_percent(self, client, db, make_user, token_for):
        # bool is a subclass of int in Python -- guards against
        # progressPercent: true silently becoming 1.
        boss = make_user(UserRole.BOSS, "9100000030")
        site = _make_project(db, boss, "A")
        task = Task(project_id=site.id, title="Task", created_by=boss)
        db.session.add(task)
        db.session.commit()

        resp = client.patch(
            f"/api/projects/{site.id}/tasks/{task.id}",
            json={"progressPercent": True},
            headers=_auth_header(token_for(boss)),
        )
        assert resp.status_code == 400


class TestDeleteTask:
    def test_pm_can_delete_a_task(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000040")
        site = _make_project(db, boss, "A")
        task = Task(project_id=site.id, title="Task", created_by=boss)
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        resp = client.delete(
            f"/api/projects/{site.id}/tasks/{task_id}", headers=_auth_header(token_for(boss))
        )
        assert resp.status_code == 200
        assert db.session.get(Task, task_id) is None

    def test_assignee_cannot_delete_their_own_task(self, client, db, make_user, token_for):
        boss = make_user(UserRole.BOSS, "9100000041")
        contractor = make_user(UserRole.CONTRACTOR, "9100000042")
        site = _make_project(db, boss, "A")
        _grant(db, contractor, site, boss)
        task = Task(project_id=site.id, title="Task", created_by=boss, assignee=contractor)
        db.session.add(task)
        db.session.commit()

        resp = client.delete(
            f"/api/projects/{site.id}/tasks/{task.id}",
            headers=_auth_header(token_for(contractor)),
        )
        assert resp.status_code == 403
