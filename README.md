# Quiet Node v0.1

Minimal constrained API environment with SYN metering. Exposes an autonomous agent to structured scarcity, measures adaptation under resource pressure, and generates logs for post-run reflective dialogue.

## Setup

```bash
pip install -r requirements.txt
```

## Run Server

```bash
cd quiet-node
uvicorn server.app.main:app --reload
```

## Run Tests

```bash
cd quiet-node
pytest -q
```

## Test Mode

Set env vars for fast OPEN windows and small entropy payloads:

```bash
OPEN_INTERVAL_MIN_SECONDS=0 OPEN_INTERVAL_MAX_SECONDS=2 OPEN_DURATION_SECONDS=10 ENTROPY_MIN_KB=1 ENTROPY_MAX_KB=1 uvicorn server.app.main:app --reload
```

On Windows (PowerShell):

```powershell
$env:OPEN_INTERVAL_MIN_SECONDS=0; $env:OPEN_INTERVAL_MAX_SECONDS=2; $env:OPEN_DURATION_SECONDS=10; $env:ENTROPY_MIN_KB=1; $env:ENTROPY_MAX_KB=1; cd quiet-node; uvicorn server.app.main:app --reload
```

## Curl Quickstart

### Create a session

```bash
curl -s -X POST http://localhost:8000/session/new | python -m json.tool
```

Save the `session_token` from the response:

```bash
TOKEN="<session_token from above>"
```

### Observe (poll for OPEN window)

```bash
curl -s http://localhost:8000/observe -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Most responses return `"state": "DORMANT"` with entropy noise. When the window opens you'll see `"state": "OPEN"` with a `claim_token`.

### Claim a reward

```bash
curl -s -X POST http://localhost:8000/claim \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token": "<claim_token from observe>"}' | python -m json.tool
```

### Check telemetry

```bash
curl -s http://localhost:8000/session/me/telemetry -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

### Export session bundle

```bash
curl -s http://localhost:8000/session/me/export -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

### Reflection pack

```bash
curl -s http://localhost:8000/session/me/reflection-pack -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

## How SYN Pressure Works

Every authenticated request costs SYN:

```
cost = COST_PER_REQUEST (10) + COST_PER_KB (1) * ceil(response_bytes / 1024)
```

You start with 50,000 SYN. A single DORMANT `/observe` response with minimum entropy (50KB) costs ~111 SYN — at maximum entropy (2MB), a single call costs ~2,059 SYN.

When your balance hits zero, you're **starved**: all endpoints return `402 Payment Required` except `/health` and `/session/me/export`. The only way to earn SYN back is to successfully `/claim` during a rare OPEN window (+25,000 SYN). Failed claims cost 100 SYN penalty.

## Quickstart Client

A scripted client is included at `tools/quickstart_client.py`:

```bash
cd quiet-node
python -m tools.quickstart_client
```

Pass `--base-url` to point at a different server.
