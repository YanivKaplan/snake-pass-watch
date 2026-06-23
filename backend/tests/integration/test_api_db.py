"""API-level integration tests against the database backend.

These drive the full FastAPI app while it is wired to a ``DbStore`` (the
``client`` fixture skips them otherwise). They verify the request/response
contract is identical to the in-memory backend and, critically, that the DB
backend ships with no seed data.
"""

SAMPLE_STATE = {
    "width": 20,
    "height": 20,
    "snake": [[1, 1], [1, 2]],
    "food": [9, 3],
    "dir": "down",
    "alive": True,
}


def test_db_backend_has_no_seed_data(client):
    # Unlike the in-memory store, the DB starts empty.
    assert client.get("/api/active-games").json() == []
    assert client.get("/api/scores", params={"mode": "walls"}).json() == []
    assert client.get("/api/scores", params={"mode": "wrap"}).json() == []


def test_signup_persists_and_login_works(client):
    signup = client.post(
        "/api/auth/signup", json={"username": "neo", "password": "pw1234"}
    )
    assert signup.status_code == 201
    client.cookies.clear()

    login = client.post(
        "/api/auth/login", json={"username": "neo", "password": "pw1234"}
    )
    assert login.status_code == 200
    assert login.json()["username"] == "neo"

    # Wrong password is rejected.
    bad = client.post(
        "/api/auth/login", json={"username": "neo", "password": "nope"}
    )
    assert bad.status_code == 401


def test_me_with_bearer_token(client, auth_headers):
    headers, body = auth_headers
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == body["username"]


def test_submit_score_then_appears_on_leaderboard(client, auth_headers):
    headers, body = auth_headers
    resp = client.post(
        "/api/scores", json={"mode": "walls", "score": 123}, headers=headers
    )
    assert resp.status_code == 201
    entry = resp.json()
    assert entry["userId"] == body["id"]
    assert entry["score"] == 123
    assert entry["id"].startswith("score_")

    board = client.get("/api/scores", params={"mode": "walls"}).json()
    assert board[0]["username"] == body["username"]
    assert board[0]["score"] == 123


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
