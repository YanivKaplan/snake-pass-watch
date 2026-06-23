"""Additional API-level integration coverage against the temporary DB.

Complements ``test_full_flow`` with the remaining endpoints (auth checks, live
game publish/fetch/end) and verifies the DB backend ships with no seed data.
"""

import pytest

SAMPLE_STATE = {
    "width": 20,
    "height": 20,
    "snake": [[1, 1], [1, 2]],
    "food": [9, 3],
    "dir": "down",
    "alive": True,
}


@pytest.fixture()
def auth_headers(client):
    """Sign up a fresh user; return (bearer headers, user dict)."""
    resp = client.post(
        "/api/auth/signup", json={"username": "itester", "password": "secret"}
    )
    assert resp.status_code == 201
    body = resp.json()
    client.cookies.clear()
    return {"Authorization": f"Bearer {body['token']}"}, body


def test_db_backend_has_no_seed_data(client):
    # Unlike the in-memory store, the DB starts empty.
    assert client.get("/api/active-games").json() == []
    assert client.get("/api/scores", params={"mode": "walls"}).json() == []
    assert client.get("/api/scores", params={"mode": "wrap"}).json() == []


def test_login_wrong_password_is_rejected(client):
    client.post("/api/auth/signup", json={"username": "neo", "password": "pw1234"})
    client.cookies.clear()
    bad = client.post(
        "/api/auth/login", json={"username": "neo", "password": "nope"}
    )
    assert bad.status_code == 401


def test_me_with_bearer_token(client, auth_headers):
    headers, body = auth_headers
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == body["username"]


def test_publish_fetch_and_end_game(client, auth_headers):
    headers, body = auth_headers
    uid = body["id"]

    pub = client.put(
        "/api/active-games/me",
        json={"state": SAMPLE_STATE, "mode": "wrap", "score": 7},
        headers=headers,
    )
    assert pub.status_code == 204

    game = client.get(f"/api/active-games/{uid}").json()
    assert game["userId"] == uid
    assert game["score"] == 7
    assert game["state"]["snake"][0] == [1, 1]
    assert client.get("/api/active-games").json()[0]["userId"] == uid

    ended = client.delete("/api/active-games/me", headers=headers)
    assert ended.status_code == 204
    assert client.get(f"/api/active-games/{uid}").json() is None


def test_submit_score_requires_auth(client):
    resp = client.post("/api/scores", json={"mode": "walls", "score": 10})
    assert resp.status_code == 401
