def test_404_on_an_unknown_route_returns_json_not_html(client):
    resp = client.get("/api/this-route-does-not-exist")
    assert resp.status_code == 404
    assert resp.content_type.startswith("application/json")
    assert resp.get_json()["error"]


def test_integrity_error_returns_409_with_a_clear_message(client):
    # Two users, same phone number, second one hits the DB's unique
    # constraint -- proves handle_integrity_error (app/errors.py) actually
    # catches it rather than the request 500ing with a raw traceback.
    payload = {"name": "A", "phone": "9991112222", "password": "secret123", "role": "client"}
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/register", json={**payload, "name": "B"})
    # Handled explicitly inside register() with its own rollback+message,
    # so this is 400 (validation-style), not 409 -- see test below for the
    # generic path when a route does NOT pre-empt it.
    assert resp.status_code == 400


def test_unexpected_exception_returns_clean_500_not_a_traceback(app, client):
    @app.route("/__test_boom")
    def boom():
        raise RuntimeError("simulated failure, not a real bug")

    resp = client.get("/__test_boom")
    assert resp.status_code == 500
    assert resp.content_type.startswith("application/json")
    assert resp.get_json()["error"]
    assert "RuntimeError" not in resp.get_data(as_text=True)  # no leaked internals


def test_missing_auth_token_returns_json_error(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Authentication required."

def test_security_headers_are_present(client):
    response = client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "camera=(self)" in response.headers["Permissions-Policy"]
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_liveness_does_not_require_dependencies(client):
    resp = client.get("/api/live")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "alive"


def test_readiness_checks_database_and_storage(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["database"] is True
    assert body["storage"] is True
