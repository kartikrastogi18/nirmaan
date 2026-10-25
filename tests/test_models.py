import pytest

from app.models import Project, ProjectAccess, User, UserRole, generate_public_id
from app.services.access_control import require_project_access, visible_project_ids


def _make_user(db, role, phone, name="Test User"):
    user = User(
        public_id=generate_public_id(role),
        name=name,
        phone=phone,
        role=role,
    )
    user.set_password("secret123")
    db.session.add(user)
    db.session.commit()
    return user


def _make_project(db, boss, code="A", name="Skyline Residency"):
    project = Project(site_code=code, name=name, created_by=boss)
    db.session.add(project)
    db.session.commit()
    return project


class TestPasswordHashing:
    def test_password_is_never_stored_as_plaintext(self, db):
        user = _make_user(db, UserRole.CONTRACTOR, "9990000001")
        assert user.password_hash != "secret123"
        assert "secret123" not in user.password_hash

    def test_check_password_accepts_correct_and_rejects_wrong(self, db):
        user = _make_user(db, UserRole.CONTRACTOR, "9990000002")
        assert user.check_password("secret123") is True
        assert user.check_password("wrong-password") is False

    def test_short_password_is_rejected(self, db):
        user = User(
            public_id=generate_public_id(UserRole.CLIENT),
            name="Too Short",
            phone="9990000003",
            role=UserRole.CLIENT,
        )
        with pytest.raises(ValueError):
            user.set_password("abc")


class TestSiteIsolation:
    def test_boss_can_access_every_project_with_no_explicit_grant(self, db):
        boss = _make_user(db, UserRole.BOSS, "9990000010")
        site_a = _make_project(db, boss, "A", "Skyline Residency")
        site_b = _make_project(db, boss, "B", "Green Valley")

        assert require_project_access(boss, site_a.id) is True
        assert require_project_access(boss, site_b.id) is True
        assert sorted(visible_project_ids(boss)) == sorted([site_a.id, site_b.id])

    def test_contractor_is_isolated_to_their_assigned_site_only(self, db):
        boss = _make_user(db, UserRole.BOSS, "9990000011")
        contractor = _make_user(db, UserRole.CONTRACTOR, "9990000012")

        site_a = _make_project(db, boss, "A", "Skyline Residency")
        site_b = _make_project(db, boss, "B", "Green Valley")

        db.session.add(
            ProjectAccess(user_id=contractor.id, project_id=site_a.id, granted_by_id=boss.id)
        )
        db.session.commit()

        assert require_project_access(contractor, site_a.id) is True
        assert require_project_access(contractor, site_b.id) is False
        assert visible_project_ids(contractor) == [site_a.id]

    def test_client_sees_only_their_own_project(self, db):
        boss = _make_user(db, UserRole.BOSS, "9990000013")
        client = _make_user(db, UserRole.CLIENT, "9990000014")

        site_a = _make_project(db, boss, "A", "Skyline Residency")
        site_b = _make_project(db, boss, "B", "Green Valley")

        db.session.add(
            ProjectAccess(user_id=client.id, project_id=site_b.id, granted_by_id=boss.id)
        )
        db.session.commit()

        assert require_project_access(client, site_a.id) is False
        assert require_project_access(client, site_b.id) is True

    def test_duplicate_access_grant_is_rejected_at_the_db_level(self, db):
        boss = _make_user(db, UserRole.BOSS, "9990000015")
        pm = _make_user(db, UserRole.PROJECT_MANAGER, "9990000016")
        site_a = _make_project(db, boss, "A", "Skyline Residency")

        db.session.add(ProjectAccess(user_id=pm.id, project_id=site_a.id, granted_by_id=boss.id))
        db.session.commit()

        db.session.add(ProjectAccess(user_id=pm.id, project_id=site_a.id, granted_by_id=boss.id))
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

    def test_revoking_access_removes_visibility(self, db):
        boss = _make_user(db, UserRole.BOSS, "9990000017")
        architect = _make_user(db, UserRole.ARCHITECT, "9990000018")
        site_a = _make_project(db, boss, "A", "Skyline Residency")

        grant = ProjectAccess(user_id=architect.id, project_id=site_a.id, granted_by_id=boss.id)
        db.session.add(grant)
        db.session.commit()
        assert require_project_access(architect, site_a.id) is True

        db.session.delete(grant)
        db.session.commit()
        assert require_project_access(architect, site_a.id) is False


class TestCascadeCleanup:
    def test_deleting_a_project_removes_its_access_grants(self, db):
        boss = _make_user(db, UserRole.BOSS, "9990000020")
        pm = _make_user(db, UserRole.PROJECT_MANAGER, "9990000021")
        site_a = _make_project(db, boss, "A", "Skyline Residency")

        db.session.add(ProjectAccess(user_id=pm.id, project_id=site_a.id, granted_by_id=boss.id))
        db.session.commit()

        db.session.delete(site_a)
        db.session.commit()

        assert ProjectAccess.query.filter_by(user_id=pm.id).count() == 0
