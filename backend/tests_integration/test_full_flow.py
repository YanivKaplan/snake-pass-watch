"""End-to-end user flow against a temporary SQLite database.

Exercises the full path a real client takes — sign up, log in, submit a score,
then read it back from the leaderboard — through the live FastAPI app and the
persistent ``DbStore`` backend.
"""

from fastapi.testclient import TestClient

from app.main import app


def test_signup_login_submit_score_read_leaderboard(client):
    # 1. Sign up.
    signup = client.post(
        "/api/auth/signup", json={"username": "yaniv", "password": "pw1234"}
    )
    assert signup.status_code == 201
    user = signup.json()
    assert user["username"] == "yaniv"
    # Drop the signup cookie so the login below is exercised in isolation.
    client.cookies.clear()

    # 2. Log in.
    login = client.post(
        "/api/auth/login", json={"username": "yaniv", "password": "pw1234"}
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Submit a score.
    submit = client.post(
        "/api/scores", json={"mode": "walls", "score": 77}, headers=headers
    )
    assert submit.status_code == 201
    submitted = submit.json()
    assert submitted["userId"] == user["id"]
    assert submitted["score"] == 77

    # 4. Read it back from the leaderboard.
    board = client.get("/api/scores", params={"mode": "walls"}).json()
    assert len(board) == 1
    assert board[0]["userId"] == user["id"]
    assert board[0]["username"] == "yaniv"
    assert board[0]["score"] == 77


def test_full_flow_persists_to_the_database(client):
    """The submitted score is durable: it survives an app (lifespan) restart."""
    client.post("/api/auth/signup", json={"username": "neo", "password": "pw1234"})
    token = client.post(
        "/api/auth/login", json={"username": "neo", "password": "pw1234"}
    ).json()["token"]
    client.post(
        "/api/scores",
        json={"mode": "wrap", "score": 51},
        headers={"Authorization": f"Bearer {token}"},
    )

    # A brand-new client re-enters the app lifespan (reset is non-destructive
    # for the DB backend); the score is still there.
    with TestClient(app) as fresh_client:
        board = fresh_client.get("/api/scores", params={"mode": "wrap"}).json()
    assert board[0]["username"] == "neo"
    assert board[0]["score"] == 51
