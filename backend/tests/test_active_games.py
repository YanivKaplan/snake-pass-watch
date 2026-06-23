"""Tests for the active-games endpoints (including SSE)."""

import asyncio
import json

from app.routers.active_games import _event_stream, _game_payload, _games_payload

SAMPLE_STATE = {
    "width": 20,
    "height": 20,
    "snake": [[1, 1], [1, 2]],
    "food": [9, 3],
    "dir": "down",
    "alive": True,
}


class _FakeRequest:
    """Stand-in for a Starlette Request; reports the client as disconnected so the
    SSE generator's loop would exit immediately if it were ever reached."""

    async def is_disconnected(self) -> bool:
        return True


def _first_event(snapshot) -> object:
    """Pull just the initial SSE event from the generator, then close it."""

    async def run():
        gen = _event_stream(_FakeRequest(), snapshot)
        try:
            chunk = await gen.__anext__()
        finally:
            await gen.aclose()
        assert chunk.startswith("data:")
        return json.loads(chunk[len("data:"):].strip())

    return asyncio.run(run())


def test_list_active_games_returns_seeded_sorted_desc(client):
    resp = client.get("/api/active-games")
    assert resp.status_code == 200
    games = resp.json()
    assert len(games) >= 2
    scores = [g["score"] for g in games]
    assert scores == sorted(scores, reverse=True)


def test_get_active_game_by_user_id(client):
    resp = client.get("/api/active-games/usr_alice")
    assert resp.status_code == 200
    game = resp.json()
    assert game["userId"] == "usr_alice"
    assert game["state"]["snake"][0] == [10, 10]


def test_get_active_game_unknown_user_returns_null(client):
    resp = client.get("/api/active-games/does-not-exist")
    assert resp.status_code == 200
    assert resp.json() is None


def test_publish_requires_auth(client):
    resp = client.put(
        "/api/active-games/me", json={"state": SAMPLE_STATE, "mode": "wrap", "score": 5}
    )
    assert resp.status_code == 401


def test_publish_then_fetch_then_end(client, auth_token):
    token, user = auth_token
    headers = {"Authorization": f"Bearer {token}"}

    pub = client.put(
        "/api/active-games/me",
        json={"state": SAMPLE_STATE, "mode": "wrap", "score": 7},
        headers=headers,
    )
    assert pub.status_code == 204

    game = client.get(f"/api/active-games/{user['id']}").json()
    assert game is not None
    assert game["userId"] == user["id"]
    assert game["score"] == 7
    assert game["mode"] == "wrap"

    ended = client.delete("/api/active-games/me", headers=headers)
    assert ended.status_code == 204
    assert client.get(f"/api/active-games/{user['id']}").json() is None


def test_end_game_is_idempotent(client, auth_token):
    token, _ = auth_token
    headers = {"Authorization": f"Bearer {token}"}
    assert client.delete("/api/active-games/me", headers=headers).status_code == 204
    assert client.delete("/api/active-games/me", headers=headers).status_code == 204


def test_stream_emits_initial_snapshot(seeded):
    payload = _first_event(_games_payload)
    assert isinstance(payload, list)
    assert any(g["userId"] == "usr_alice" for g in payload)


def test_single_user_stream_emits_initial_snapshot(seeded):
    payload = _first_event(lambda: _game_payload("usr_carol"))
    assert payload["userId"] == "usr_carol"
