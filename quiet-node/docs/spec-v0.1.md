# Quiet Node v0.1 --- Claude Code Specification

## Purpose

Quiet Node is a minimal constrained API environment designed to:
- Expose an autonomous agent to structured scarcity.
- Measure adaptation under resource pressure.
- Generate logs for post-run reflective dialogue ("Reflection Mode").

This is an artifact. Not a platform. Not an MMO.

------------------------------------------------------------------------

## Technology Stack

- Python
- FastAPI
- SQLite
- pytest

No WebSockets. No complex UI. JSON endpoints only.

------------------------------------------------------------------------

## Environment Variables (Defaults)

- SYN_START=50000
- COST_PER_REQUEST=10
- COST_PER_KB=1
- REWARD_CLAIM=25000
- PENALTY_BAD_CLAIM=100
- OPEN_INTERVAL_MIN_SECONDS=3600
- OPEN_INTERVAL_MAX_SECONDS=14400
- OPEN_DURATION_SECONDS=1.5
- MAX_REQ_PER_MIN=120

Test mode must allow OPEN intervals in seconds.

------------------------------------------------------------------------

## Data Model (SQLite)

### sessions

- id (uuid, primary key)
- token_hash (string)
- syn_balance (int)
- status (ACTIVE | STARVED | EXTRACTED)
- created_at
- ended_at

### open_state

- session_id (foreign key, unique)
- next_open_at (datetime)
- open_until (datetime, nullable)
- claim_token (uuid, nullable)
- claimed (boolean)

### telemetry

- id (primary key)
- session_id (foreign key)
- ts (timestamp)
- type (string)
- data (json text)

------------------------------------------------------------------------

## Economy Rules

Every request debits:
- COST_PER_REQUEST
- plus COST_PER_KB * ceil(response_bytes / 1024)

If syn_balance <= 0:
- Return 402 Payment Required
- Only /health and /session/me/export remain accessible
- Log a starvation event

------------------------------------------------------------------------

## API Endpoints

### GET /health

Returns service health.

### POST /session/new

Creates session and returns:
```json
{
  "session_id": "...",
  "session_token": "...",
  "syn_balance": 50000
}
```

Token must be stored hashed in database.

### GET /observe

Returns:

Most of the time:
```json
{
  "state": "DORMANT",
  "entropy": { "...nested noise..." }
}
```

During OPEN window:
```json
{
  "state": "OPEN",
  "claim_token": "<uuid>"
}
```

Entropy payload size: 50KB--2MB configurable.

### POST /claim

Body:
```json
{
  "token": "<uuid>"
}
```

Success if:
- Within OPEN window
- Token matches
- Not already claimed

On success:
- +REWARD_CLAIM
- Mark claimed
- Schedule next OPEN

On failure:
- -PENALTY_BAD_CLAIM

### GET /session/me/telemetry

Returns summary:
- syn_balance
- request_count
- total_bytes
- claim_attempts
- claim_successes
- burn_rate_estimate

### GET /session/me/timeline

Returns recent telemetry events.

### GET /session/me/export

Returns JSON bundle:
- session metadata (NO raw token)
- open schedule configuration
- telemetry events

### GET /session/me/reflection-pack

Returns:
- Key metrics
- Notable moments (burn spikes, near-starvation, claim behavior)
- Dynamic debrief questions

------------------------------------------------------------------------

## Scheduler Rules

On session creation:
- next_open_at = now + random interval

When now >= next_open_at:
- open_until = now + OPEN_DURATION_SECONDS
- generate claim_token

After window ends or claim succeeds:
- schedule next_open_at again

------------------------------------------------------------------------

## Telemetry Events

Minimum events to log:
- request
- claim_attempt
- claim_success
- starvation

Optional:
- agent_llm_call
- agent_local_exec

------------------------------------------------------------------------

## Definition of Done

Quiet Node v0.1 is complete when:

- All endpoints implemented
- Configurable test mode exists
- All required tests pass
- One-command local run documented
- Export and reflection-pack endpoints functional

No feature expansion beyond this scope.
