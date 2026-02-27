# Quiet Node v0.1 — Claude Code Instructions

## Goal
Ship Quiet Node v0.1: minimal constrained API (no websockets) with SYN metering, /observe rare OPEN windows, /claim, telemetry, export, reflection-pack.

## Non-goals (v0.1)
- No MMO / marketplace / PvP / websockets.
- No complex UI. JSON endpoints only.
- No "future-proofing" or v0.2.

## Tech choices
- Python + FastAPI
- SQLite
- pytest

## Workflow
- Work in small milestones.
- After each milestone: run tests (`pytest -q`) and show output summary.
- Prefer simple, readable code.

## Definition of Done
Endpoints implemented and tested:
- GET /health
- POST /session/new
- GET /observe
- POST /claim
- GET /session/me/telemetry
- GET /session/me/timeline
- GET /session/me/export
- GET /session/me/reflection-pack
Plus: configurable test-mode where OPEN occurs in seconds.
