import pytest
from datetime import datetime, timedelta, timezone

from server.app.main import app


async def _create_session(client):
    resp = await client.post("/session/new")
    body = resp.json()
    return body["session_id"], body["session_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_observe_returns_dormant_initially(client):
    sid, token = await _create_session(client)

    resp = await client.get("/observe", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "DORMANT"
    assert "entropy" in body
    # Entropy should be a hex string of at least 50KB
    assert len(body["entropy"]) >= 50 * 1024 * 2  # hex = 2 chars per byte


@pytest.mark.anyio
async def test_observe_returns_open_when_window_active(client):
    sid, token = await _create_session(client)

    # Force next_open_at into the past so the window opens
    db = app.state.db
    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    db.execute(
        "INSERT INTO open_state (session_id, next_open_at, claimed) VALUES (?, ?, 0)",
        (sid, past),
    )
    db.commit()

    resp = await client.get("/observe", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "OPEN"
    assert "claim_token" in body


@pytest.mark.anyio
async def test_claim_token_stable_during_open_window(client):
    sid, token = await _create_session(client)

    # Force open window: next_open_at in the past, long duration
    db = app.state.db
    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    far_future = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()
    db.execute(
        "INSERT INTO open_state (session_id, next_open_at, claimed) VALUES (?, ?, 0)",
        (sid, past),
    )
    db.commit()

    # First observe opens the window
    resp1 = await client.get("/observe", headers=_auth(token))
    body1 = resp1.json()
    assert body1["state"] == "OPEN"

    # Second observe returns same claim_token
    resp2 = await client.get("/observe", headers=_auth(token))
    body2 = resp2.json()
    assert body2["state"] == "OPEN"
    assert body2["claim_token"] == body1["claim_token"]


@pytest.mark.anyio
async def test_window_expires_and_reschedules(client):
    sid, token = await _create_session(client)

    # Force an already-expired window
    db = app.state.db
    past = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    expired = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    db.execute(
        "INSERT INTO open_state (session_id, next_open_at, open_until, claim_token, claimed) "
        "VALUES (?, ?, ?, 'old-token', 0)",
        (sid, past, expired),
    )
    db.commit()

    resp = await client.get("/observe", headers=_auth(token))
    body = resp.json()
    assert body["state"] == "DORMANT"

    # Verify rescheduled: next_open_at should be in the future
    row = db.execute(
        "SELECT next_open_at FROM open_state WHERE session_id = ?", (sid,)
    ).fetchone()
    next_at = datetime.fromisoformat(row["next_open_at"])
    assert next_at > datetime.now(timezone.utc)
