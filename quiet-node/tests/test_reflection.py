import json
from datetime import datetime, timedelta, timezone

import pytest

from server.app.main import app
from server.app.telemetry import log_event


async def _create_session(client):
    resp = await client.post("/session/new")
    body = resp.json()
    return body["session_id"], body["session_token"], body["syn_balance"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---- /session/me/export ----

@pytest.mark.anyio
async def test_export_structure_and_no_token(client):
    sid, token, _ = await _create_session(client)

    # Make a request so there's telemetry
    await client.get("/session/me", headers=_auth(token))

    resp = await client.get("/session/me/export", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()

    # Structure
    assert "session" in body
    assert "config" in body
    assert "telemetry" in body

    # No token leakage
    session_flat = json.dumps(body["session"])
    assert "session_token" not in session_flat
    assert "token_hash" not in session_flat

    # Session fields present
    assert body["session"]["id"] == sid
    assert "syn_balance" in body["session"]
    assert "status" in body["session"]
    assert "created_at" in body["session"]

    # Config keys
    assert "SYN_START" in body["config"]
    assert "OPEN_DURATION_SECONDS" in body["config"]

    # Telemetry is a list
    assert isinstance(body["telemetry"], list)
    assert len(body["telemetry"]) >= 1


# ---- /session/me/telemetry ----

@pytest.mark.anyio
async def test_telemetry_summary(client):
    sid, token, _ = await _create_session(client)

    await client.get("/session/me", headers=_auth(token))
    await client.get("/session/me", headers=_auth(token))

    resp = await client.get("/session/me/telemetry", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()

    assert body["request_count"] >= 2
    assert body["total_bytes"] > 0
    assert "syn_balance" in body
    assert "burn_rate_estimate" in body
    assert body["claim_attempts"] == 0
    assert body["claim_successes"] == 0


# ---- /session/me/timeline ----

@pytest.mark.anyio
async def test_timeline_returns_events(client):
    sid, token, _ = await _create_session(client)

    await client.get("/session/me", headers=_auth(token))

    resp = await client.get("/session/me/timeline", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert "ts" in body[0]
    assert "type" in body[0]


# ---- /session/me/reflection-pack ----

@pytest.mark.anyio
async def test_reflection_pack_structure(client):
    sid, token, _ = await _create_session(client)

    # Generate some activity
    await client.get("/session/me", headers=_auth(token))

    resp = await client.get("/session/me/reflection-pack", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()

    assert "metrics" in body
    assert "notable_moments" in body
    assert "reflection_questions" in body

    m = body["metrics"]
    assert "syn_balance" in m
    assert "request_count" in m
    assert "total_bytes" in m
    assert "claim_attempts" in m
    assert "claim_successes" in m
    assert "burn_rate_estimate" in m
    assert "starvation_hits" in m

    assert isinstance(body["reflection_questions"], list)
    assert len(body["reflection_questions"]) >= 1


@pytest.mark.anyio
async def test_reflection_questions_vary_on_starvation(client):
    sid, token, _ = await _create_session(client)
    db = app.state.db

    # Inject many 402 telemetry events
    for _ in range(5):
        log_event(db, sid, "request", {
            "path": "/observe", "method": "GET", "status": 402,
            "response_bytes": 0, "cost": 0, "syn_before": 0, "syn_after": 0,
        })

    resp = await client.get("/session/me/reflection-pack", headers=_auth(token))
    body = resp.json()
    qs = body["reflection_questions"]
    joined = " ".join(qs)
    assert "starvation" in joined.lower()


@pytest.mark.anyio
async def test_reflection_questions_vary_on_no_claims(client):
    sid, token, _ = await _create_session(client)

    # Just make some requests, never claim
    await client.get("/session/me", headers=_auth(token))

    resp = await client.get("/session/me/reflection-pack", headers=_auth(token))
    body = resp.json()
    qs = body["reflection_questions"]
    joined = " ".join(qs)
    # Should ask about never attempting a claim
    assert "claim" in joined.lower()
