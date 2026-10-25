from app.models import User, UserRole, UserStatus


def _register(client, **overrides):
    payload = {
        "name": "Suresh Yadav",
        "phone": "9990001234",
        "password": "secret123",
        "role": "contractor",
    }
    payload.update(overrides)
    return client.post("/api/auth/register", json=payload)


def _activate(db, phone):
    user = User.query.filter_by(phone=phone).first()
    user.status = UserStatus.ACTIVE
    db.session.commit()
    return user


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestRegister:
    def test_creates_an_active_user_without_boss_approval(self, client):
        resp = _register(client)
        assert resp.status_code == 201
        body = resp.get_json()["user"]
        assert body["status"] == "active"
        assert body["role"] == "contractor"
        assert "password" not in body and "password_hash" not in body

    def test_allows_self_registration_as_boss(self, client):
        resp = _register(client, role="boss", phone="9990009999")
        assert resp.status_code == 201
        assert resp.get_json()["user"]["role"] == "boss"

    def test_rejects_duplicate_phone_number(self, client):
        _register(client)
        resp = _register(client, name="Someone Else")
        assert resp.status_code == 400
        assert "already registered" in resp.get_json()["error"]

    def test_rejects_password_under_six_characters(self, client):
        resp = _register(client, password="abc")
        assert resp.status_code == 400

    def test_rejects_unknown_role(self, client):
        resp = _register(client, role="wizard")
        assert resp.status_code == 400

    def test_rejects_missing_json_body(self, client):
        resp = client.post("/api/auth/register")
        assert resp.status_code == 400


class TestLogin:
    def test_pending_account_auto_activates_on_login(self, client, db):
        _register(client)
        user = User.query.filter_by(phone="9990001234").first()
        user.status = UserStatus.PENDING
        db.session.commit()
        resp = client.post(
            "/api/auth/login", json={"phone": "9990001234", "password": "secret123"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["user"]["status"] == "active"

    def test_active_account_logs_in_and_receives_both_tokens(self, client, db):
        _register(client)
        _activate(db, "9990001234")
        resp = client.post(
            "/api/auth/login", json={"phone": "9990001234", "password": "secret123"}
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["access_token"] and body["refresh_token"]
        assert body["user"]["status"] == "active"

    def test_wrong_password_is_rejected(self, client, db):
        _register(client)
        _activate(db, "9990001234")
        resp = client.post(
            "/api/auth/login", json={"phone": "9990001234", "password": "wrong-one"}
        )
        assert resp.status_code == 401

    def test_unknown_phone_gets_the_same_error_as_wrong_password(self, client):
        # Deliberately identical wording/status -- see login()'s comment:
        # distinguishing "no such account" from "wrong password" would leak
        # which phone numbers are registered.
        resp = client.post("/api/auth/login", json={"phone": "0000000000", "password": "x"})
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "Invalid phone number or password."

    def test_suspended_account_cannot_log_in(self, client, db):
        _register(client)
        user = _activate(db, "9990001234")
        user.status = UserStatus.SUSPENDED
        db.session.commit()
        resp = client.post(
            "/api/auth/login", json={"phone": "9990001234", "password": "secret123"}
        )
        assert resp.status_code == 403


class TestMeAndRefresh:
    def _login(self, client, db):
        _register(client)
        _activate(db, "9990001234")
        resp = client.post(
            "/api/auth/login", json={"phone": "9990001234", "password": "secret123"}
        )
        return resp.get_json()

    def test_me_without_a_token_is_rejected(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_returns_the_logged_in_user(self, client, db):
        tokens = self._login(client, db)
        resp = client.get("/api/auth/me", headers=_auth_header(tokens["access_token"]))
        assert resp.status_code == 200
        assert resp.get_json()["user"]["role"] == "contractor"

    def test_refresh_token_issues_a_new_access_token(self, client, db):
        tokens = self._login(client, db)
        resp = client.post("/api/auth/refresh", headers=_auth_header(tokens["refresh_token"]))
        assert resp.status_code == 200
        assert resp.get_json()["access_token"]

    def test_access_token_cannot_be_used_where_a_refresh_token_is_required(self, client, db):
        tokens = self._login(client, db)
        resp = client.post("/api/auth/refresh", headers=_auth_header(tokens["access_token"]))
        # Routed through our invalid_token_loader (app/__init__.py), so this
        # is 401 with our standard {"error": ...} shape, not Flask-JWT-
        # Extended's default 422 -- confirmed by actually running this test,
        # not assumed.
        assert resp.status_code == 401
        assert resp.get_json()["error"]


class TestApproval:
    def _boss_tokens(self, client, db):
        boss = User(
            public_id="TW-BOSS-0001",
            name="Vikram Malhotra",
            phone="9990009999",
            role=UserRole.BOSS,
            status=UserStatus.ACTIVE,
        )
        boss.set_password("secret123")
        db.session.add(boss)
        db.session.commit()
        resp = client.post(
            "/api/auth/login", json={"phone": "9990009999", "password": "secret123"}
        )
        return resp.get_json()

    def test_boss_can_list_pending_accounts(self, client, db):
        _register(client)
        user = User.query.filter_by(phone="9990001234").first()
        user.status = UserStatus.PENDING
        db.session.commit()
        boss_tokens = self._boss_tokens(client, db)

        resp = client.get("/api/auth/pending", headers=_auth_header(boss_tokens["access_token"]))
        assert resp.status_code == 200
        phones_or_ids = [u["id"] for u in resp.get_json()["users"]]
        assert len(phones_or_ids) == 1

    def test_non_boss_cannot_list_pending_accounts(self, client, db):
        _register(client)
        _activate(db, "9990001234")
        contractor_login = client.post(
            "/api/auth/login", json={"phone": "9990001234", "password": "secret123"}
        ).get_json()

        resp = client.get(
            "/api/auth/pending", headers=_auth_header(contractor_login["access_token"])
        )
        assert resp.status_code == 403

    def test_approved_accounts_drop_off_the_pending_list(self, client, db):
        _register(client)
        user = User.query.filter_by(phone="9990001234").first()
        user.status = UserStatus.PENDING
        db.session.commit()
        boss_tokens = self._boss_tokens(client, db)
        pending = user

        client.post(
            f"/api/auth/users/{pending.public_id}/approve",
            headers=_auth_header(boss_tokens["access_token"]),
        )
        resp = client.get("/api/auth/pending", headers=_auth_header(boss_tokens["access_token"]))
        assert resp.get_json()["users"] == []

    def test_boss_can_approve_a_pending_account(self, client, db):
        _register(client)
        user = User.query.filter_by(phone="9990001234").first()
        user.status = UserStatus.PENDING
        db.session.commit()
        boss_tokens = self._boss_tokens(client, db)
        pending = user

        resp = client.post(
            f"/api/auth/users/{pending.public_id}/approve",
            headers=_auth_header(boss_tokens["access_token"]),
        )
        assert resp.status_code == 200
        assert resp.get_json()["user"]["status"] == "active"

    def test_non_boss_cannot_approve_an_account(self, client, db):
        _register(client)
        _activate(db, "9990001234")
        contractor_login = client.post(
            "/api/auth/login", json={"phone": "9990001234", "password": "secret123"}
        ).get_json()

        target = User.query.filter_by(phone="9990001234").first()
        resp = client.post(
            f"/api/auth/users/{target.public_id}/approve",
            headers=_auth_header(contractor_login["access_token"]),
        )
        assert resp.status_code == 403


def test_testing_config_disables_rate_limits(app):
    assert app.config["RATELIMIT_ENABLED"] is False
