"""Integration test: OPEN window appears via env-based scheduler, no DB injection."""

import os
import time

import pytest

from server.app.main import app


# Set test-mode env vars: tiny intervals, long window, small entropy
@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    monkeypatch.setenv("OPEN_INTERVAL_MIN_SECONDS", "0.0")
    monkeypatch.setenv("OPEN_INTERVAL_MAX_SECONDS", "0.1")
    monkeypatch.setenv("OPEN_DURATION_SECONDS", "5")
    monkeypatch.setenv("ENTROPY_MIN_KB", "1")
    monkeypatch.setenv("ENTROPY_MAX_KB", "1")


async def _create_session(client):
    resp = await client.post("/session/new")
    body = resp.json()
    return body["session_id"], body["session_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_open_appears_via_env_scheduler(client):
    """With 0–0.1s interval, OPEN must appear within a handful of retries."""
    _, token = await _create_session(client)

    found_open = False
    for _ in range(20):
        resp = await client.get("/observe", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        if body["state"] == "OPEN":
            assert "claim_token" in body
            found_open = True
            break
        time.sleep(0.05)

    assert found_open, "OPEN window never appeared within 20 retries"


@pytest.mark.anyio
async def test_claim_token_stable_via_env(client):
    """Once OPEN, repeated /observe returns the same claim_token."""
    _, token = await _create_session(client)

    # Wait for OPEN
    claim_token = None
    for _ in range(20):
        resp = await client.get("/observe", headers=_auth(token))
        body = resp.json()
        if body["state"] == "OPEN":
            claim_token = body["claim_token"]
            break
        time.sleep(0.05)

    assert claim_token is not None

    # Second call should return same token
    resp2 = await client.get("/observe", headers=_auth(token))
    body2 = resp2.json()
    assert body2["state"] == "OPEN"
    assert body2["claim_token"] == claim_token


@pytest.mark.anyio
async def test_entropy_respects_env_size(client):
    """With ENTROPY_MIN_KB=1 and ENTROPY_MAX_KB=1, payload is exactly 1KB of hex."""
    _, token = await _create_session(client)

    # Need a DORMANT response — create a fresh session with future window
    # Since interval is 0-0.1s, the first observe may already be OPEN.
    # Use a second session and set its open_state to the future manually.
    # Actually, let's just check any DORMANT response we can get.
    # With 5s window, once OPEN we won't get DORMANT. So create fresh session.
    resp = await client.post("/session/new")
    body = resp.json()
    token2 = body["session_token"]
    sid2 = body["session_id"]

    # Force this session's scheduler to far future so we get DORMANT
    from datetime import datetime, timedelta, timezone
    future = (datetime.now(timezone.utc) + timedelta(seconds=3600)).isoformat()
    app.state.db.execute(
        "INSERT INTO open_state (session_id, next_open_at, claimed) VALUES (?, ?, 0)",
        (sid2, future),
    )
    app.state.db.commit()

    resp = await client.get("/observe", headers=_auth(token2))
    body = resp.json()
    assert body["state"] == "DORMANT"
    # 1KB = 1024 bytes = 2048 hex chars
    assert len(body["entropy"]) == 2048
