"""Tests for the scores / leaderboard endpoints."""


def test_leaderboard_sorted_desc_and_best_per_user(client):
    resp = client.get("/api/scores", params={"mode": "walls"})
    assert resp.status_code == 200
    entries = resp.json()
    # One entry per user, sorted by score descending.
    scores = [e["score"] for e in entries]
    assert scores == sorted(scores, reverse=True)
    usernames = [e["username"] for e in entries]
    assert len(usernames) == len(set(usernames))
    # Alice submitted 42 and 58 in walls; her best (58) should be the entry.
    alice = next(e for e in entries if e["username"] == "alice")
    assert alice["score"] == 58


def test_leaderboard_respects_limit(client):
    resp = client.get("/api/scores", params={"mode": "wrap", "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_leaderboard_requires_mode(client):
    resp = client.get("/api/scores")
    assert resp.status_code == 400


def test_submit_score_requires_auth(client):
    resp = client.post("/api/scores", json={"mode": "walls", "score": 10})
    assert resp.status_code == 401
    assert "error" in resp.json()


def test_submit_score_with_bearer_token_then_appears_on_leaderboard(client, auth_token):
    token, user = auth_token
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/api/scores", json={"mode": "walls", "score": 999}, headers=headers)
    assert resp.status_code == 201
    entry = resp.json()
    assert entry["userId"] == user["id"]
    assert entry["username"] == user["username"]
    assert entry["score"] == 999
    assert entry["id"] and entry["createdAt"]

    board = client.get("/api/scores", params={"mode": "walls", "limit": 1}).json()
    assert board[0]["username"] == user["username"]
    assert board[0]["score"] == 999


def test_submit_score_rejects_negative(client, auth_token):
    token, _ = auth_token
    resp = client.post(
        "/api/scores", json={"mode": "walls", "score": -5}, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400
