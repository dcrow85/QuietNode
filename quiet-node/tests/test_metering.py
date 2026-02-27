import math

import pytest

from server.app.main import app


async def _create_session(client):
    resp = await client.post("/session/new")
    body = resp.json()
    return body["session_id"], body["session_token"], body["syn_balance"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_metering_debits_correctly(client):
    sid, token, bal = await _create_session(client)

    resp = await client.get("/session/me", headers=_auth(token))
    assert resp.status_code == 200
    response_bytes = len(resp.content)
    expected_cost = 10 + 1 * math.ceil(response_bytes / 1024)

    # Check balance was debited
    row = app.state.db.execute(
        "SELECT syn_balance FROM sessions WHERE id = ?", (sid,)
    ).fetchone()
    assert row["syn_balance"] == bal - expected_cost


@pytest.mark.anyio
async def test_starvation_gate_returns_402(client):
    sid, token, _ = await _create_session(client)

    # Force balance to 0
    app.state.db.execute(
        "UPDATE sessions SET syn_balance = 0, status = 'STARVED' WHERE id = ?", (sid,)
    )
    app.state.db.commit()

    resp = await client.get("/session/me", headers=_auth(token))
    assert resp.status_code == 402


@pytest.mark.anyio
async def test_export_works_when_starved(client):
    sid, token, _ = await _create_session(client)

    app.state.db.execute(
        "UPDATE sessions SET syn_balance = 0, status = 'STARVED' WHERE id = ?", (sid,)
    )
    app.state.db.commit()

    resp = await client.get("/session/me/export", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["session"]["id"] == sid
    assert "session_token" not in body["session"]


@pytest.mark.anyio
async def test_request_telemetry_logged(client):
    sid, token, _ = await _create_session(client)

    await client.get("/session/me", headers=_auth(token))

    rows = app.state.db.execute(
        "SELECT type, data FROM telemetry WHERE session_id = ?", (sid,)
    ).fetchall()
    assert len(rows) >= 1
    assert rows[0]["type"] == "request"

    import json
    data = json.loads(rows[0]["data"])
    assert data["path"] == "/session/me"
    assert "cost" in data
    assert "syn_before" in data
    assert "syn_after" in data


@pytest.mark.anyio
async def test_health_not_metered(client):
    _, token, bal = await _create_session(client)

    await client.get("/health")

    # Balance unchanged (only the /session/new was unmetered too)
    row = app.state.db.execute(
        "SELECT syn_balance FROM sessions WHERE id = (SELECT id FROM sessions LIMIT 1)"
    ).fetchone()
    assert row["syn_balance"] == bal
