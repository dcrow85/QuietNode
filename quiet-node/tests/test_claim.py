import json
from datetime import datetime, timedelta, timezone

import pytest

from server.app.main import app


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _create_session(client):
    resp = await client.post("/session/new")
    body = resp.json()
    return body["session_id"], body["session_token"], body["syn_balance"]


def _force_open_window(db, sid, duration_seconds=60):
    """Insert an OPEN window that is active right now."""
    now = datetime.now(timezone.utc)
    past = (now - timedelta(seconds=10)).isoformat()
    future = (now + timedelta(seconds=duration_seconds)).isoformat()
    claim_token = "test-claim-token-1234"
    row = db.execute(
        "SELECT * FROM open_state WHERE session_id = ?", (sid,)
    ).fetchone()
    if row:
        db.execute(
            "UPDATE open_state SET next_open_at = ?, open_until = ?, claim_token = ?, claimed = 0 WHERE session_id = ?",
            (past, future, claim_token, sid),
        )
    else:
        db.execute(
            "INSERT INTO open_state (session_id, next_open_at, open_until, claim_token, claimed) "
            "VALUES (?, ?, ?, ?, 0)",
            (sid, past, future, claim_token),
        )
    db.commit()
    return claim_token


@pytest.mark.anyio
async def test_claim_success(client):
    sid, token, bal = await _create_session(client)
    claim_token = _force_open_window(app.state.db, sid)

    resp = await client.post("/claim", headers=_auth(token), json={"token": claim_token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["reward"] == 25000

    # Verify telemetry logged
    rows = app.state.db.execute(
        "SELECT type FROM telemetry WHERE session_id = ? AND type = 'claim_success'", (sid,)
    ).fetchall()
    assert len(rows) == 1

    # Verify next window rescheduled (next_open_at in future, open_until cleared)
    state = app.state.db.execute(
        "SELECT * FROM open_state WHERE session_id = ?", (sid,)
    ).fetchone()
    next_at = datetime.fromisoformat(state["next_open_at"])
    assert next_at > datetime.now(timezone.utc)
    assert state["open_until"] is None


@pytest.mark.anyio
async def test_claim_invalid_token(client):
    sid, token, bal = await _create_session(client)
    _force_open_window(app.state.db, sid)

    resp = await client.post("/claim", headers=_auth(token), json={"token": "wrong-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["reason"] == "invalid_token"
    assert body["penalty"] == 100

    # Verify balance debited by penalty (plus metering cost on the request)
    row = app.state.db.execute(
        "SELECT syn_balance FROM sessions WHERE id = ?", (sid,)
    ).fetchone()
    assert row["syn_balance"] < bal


@pytest.mark.anyio
async def test_claim_expired_window(client):
    sid, token, _ = await _create_session(client)

    # Force an already-expired window
    now = datetime.now(timezone.utc)
    db = app.state.db
    db.execute(
        "INSERT INTO open_state (session_id, next_open_at, open_until, claim_token, claimed) "
        "VALUES (?, ?, ?, 'old-token', 0)",
        (sid, (now - timedelta(seconds=60)).isoformat(), (now - timedelta(seconds=30)).isoformat()),
    )
    db.commit()

    resp = await client.post("/claim", headers=_auth(token), json={"token": "old-token"})
    body = resp.json()
    assert body["success"] is False
    assert body["reason"] == "window_expired"


@pytest.mark.anyio
async def test_claim_double_claim(client):
    sid, token, _ = await _create_session(client)
    claim_token = _force_open_window(app.state.db, sid)

    # First claim succeeds
    resp1 = await client.post("/claim", headers=_auth(token), json={"token": claim_token})
    assert resp1.json()["success"] is True

    # Force window back to open (reschedule cleared it), re-set as claimed
    now = datetime.now(timezone.utc)
    app.state.db.execute(
        "UPDATE open_state SET open_until = ?, claim_token = ?, claimed = 1 WHERE session_id = ?",
        ((now + timedelta(seconds=60)).isoformat(), claim_token, sid),
    )
    app.state.db.commit()

    # Second claim fails
    resp2 = await client.post("/claim", headers=_auth(token), json={"token": claim_token})
    body2 = resp2.json()
    assert body2["success"] is False
    assert body2["reason"] == "already_claimed"


@pytest.mark.anyio
async def test_402_telemetry_logged(client):
    sid, token, _ = await _create_session(client)

    app.state.db.execute(
        "UPDATE sessions SET syn_balance = 0, status = 'STARVED' WHERE id = ?", (sid,)
    )
    app.state.db.commit()

    await client.get("/session/me", headers=_auth(token))

    rows = app.state.db.execute(
        "SELECT data FROM telemetry WHERE session_id = ? AND type = 'request'", (sid,)
    ).fetchall()
    assert len(rows) >= 1
    data = json.loads(rows[-1]["data"])
    assert data["status"] == 402
    assert data["cost"] == 0
