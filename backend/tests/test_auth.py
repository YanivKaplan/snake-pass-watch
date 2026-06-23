"""Tests for the auth endpoints."""

from app.store import store


def test_signup_success_sets_cookie_and_returns_token(client):
    resp = client.post("/api/auth/signup", json={"username": "newbie", "password": "pw1234"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "newbie"
    assert body["id"]
    assert body["token"]
    assert "session" in resp.cookies


def test_signup_passwords_are_hashed_not_stored_plaintext(client):
    client.post("/api/auth/signup", json={"username": "secretkeeper", "password": "pw1234"})
    record = store.get_user_by_username("secretkeeper")
    assert record is not None
    assert record.password_hash != "pw1234"
    assert record.password_hash.startswith("pbkdf2_sha256$")


def test_signup_rejects_short_username(client):
    resp = client.post("/api/auth/signup", json={"username": "a", "password": "pw1234"})
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_signup_rejects_short_password(client):
    resp = client.post("/api/auth/signup", json={"username": "abc", "password": "pw"})
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_signup_duplicate_username_is_case_insensitive(client):
    client.post("/api/auth/signup", json={"username": "Dupe", "password": "pw1234"})
    resp = client.post("/api/auth/signup", json={"username": "dupe", "password": "pw1234"})
    assert resp.status_code == 409
    assert "error" in resp.json()


def test_login_success(client):
    resp = client.post("/api/auth/login", json={"username": "alice", "password": "password1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert body["token"]


def test_login_is_case_insensitive_on_username(client):
    resp = client.post("/api/auth/login", json={"username": "ALICE", "password": "password1"})
    assert resp.status_code == 200


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": "alice", "password": "nope"})
    assert resp.status_code == 401
    assert "error" in resp.json()


def test_me_when_logged_out_returns_null(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json() is None


def test_me_with_cookie(client):
    client.post("/api/auth/login", json={"username": "bob", "password": "password2"})
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "bob"


def test_me_with_bearer_token(client):
    login = client.post("/api/auth/login", json={"username": "bob", "password": "password2"})
    token = login.json()["token"]
    client.cookies.clear()
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "bob"


def test_logout_clears_session(client):
    client.post("/api/auth/login", json={"username": "bob", "password": "password2"})
    assert client.get("/api/auth/me").json() is not None
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert client.get("/api/auth/me").json() is None
