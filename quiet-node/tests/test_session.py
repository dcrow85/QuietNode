import pytest


@pytest.mark.anyio
async def test_create_session(client):
    resp = await client.post("/session/new")
    assert resp.status_code == 200
    body = resp.json()
    assert "session_id" in body
    assert "session_token" in body
    assert body["syn_balance"] == 50000


@pytest.mark.anyio
async def test_auth_success(client):
    create = await client.post("/session/new")
    token = create.json()["session_token"]

    resp = await client.get(
        "/session/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["syn_balance"] == 50000
    assert body["status"] == "ACTIVE"


@pytest.mark.anyio
async def test_auth_missing_token(client):
    resp = await client.get("/session/me")
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_auth_bad_token(client):
    resp = await client.get(
        "/session/me", headers={"Authorization": "Bearer bad-token"}
    )
    assert resp.status_code == 401
