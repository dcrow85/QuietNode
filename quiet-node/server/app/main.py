import json
import os
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from server.app import config
from server.app.auth import hash_token, require_session
from server.app.db import init_db
from server.app.middleware import MeteringMiddleware
from server.app.scheduler import evaluate_window, reschedule
from server.app.telemetry import log_event


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.db = init_db()
    yield
    application.state.db.close()


app = FastAPI(title="Quiet Node", version="0.1.0", lifespan=lifespan)
app.add_middleware(MeteringMiddleware)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/session/new")
def session_new():
    session_id = str(uuid.uuid4())
    session_token = str(uuid.uuid4())
    token_h = hash_token(session_token)
    now = datetime.now(timezone.utc).isoformat()

    db = app.state.db
    db.execute(
        "INSERT INTO sessions (id, token_hash, syn_balance, status, created_at) "
        "VALUES (?, ?, ?, 'ACTIVE', ?)",
        (session_id, token_h, config.SYN_START(), now),
    )
    db.commit()

    return {
        "session_id": session_id,
        "session_token": session_token,
        "syn_balance": config.SYN_START(),
    }


@app.get("/session/me")
def session_me(session=Depends(require_session)):
    return {
        "session_id": session["id"],
        "syn_balance": session["syn_balance"],
        "status": session["status"],
    }


@app.get("/observe")
def observe(session=Depends(require_session)):
    db = app.state.db
    window = evaluate_window(db, session["id"])

    if window["state"] == "OPEN":
        return {"state": "OPEN", "claim_token": window["claim_token"]}

    # DORMANT — return entropy noise
    size_kb = random.randint(config.ENTROPY_MIN_KB(), config.ENTROPY_MAX_KB())
    entropy = os.urandom(size_kb * 1024).hex()
    return {"state": "DORMANT", "entropy": entropy}


class ClaimBody(BaseModel):
    token: str


@app.post("/claim")
def claim(body: ClaimBody, session=Depends(require_session)):
    db = app.state.db
    sid = session["id"]
    row = db.execute(
        "SELECT * FROM open_state WHERE session_id = ?", (sid,)
    ).fetchone()

    def _fail(reason: str):
        penalty = config.PENALTY_BAD_CLAIM()
        db.execute(
            "UPDATE sessions SET syn_balance = syn_balance - ? WHERE id = ?",
            (penalty, sid),
        )
        db.commit()
        log_event(db, sid, "claim_attempt", {"success": False, "reason": reason})
        return {"success": False, "reason": reason, "penalty": penalty}

    # No open_state row or window not started
    if row is None or row["open_until"] is None:
        return _fail("no_open_window")

    now = datetime.now(timezone.utc)
    open_until = datetime.fromisoformat(row["open_until"])

    if now > open_until:
        return _fail("window_expired")

    if row["claimed"]:
        return _fail("already_claimed")

    if body.token != row["claim_token"]:
        return _fail("invalid_token")

    # Success
    reward = config.REWARD_CLAIM()
    db.execute(
        "UPDATE sessions SET syn_balance = syn_balance + ? WHERE id = ?",
        (reward, sid),
    )
    db.execute(
        "UPDATE open_state SET claimed = 1 WHERE session_id = ?", (sid,)
    )
    db.commit()
    reschedule(db, sid)
    log_event(db, sid, "claim_success", {"reward": reward})

    new_bal = db.execute(
        "SELECT syn_balance FROM sessions WHERE id = ?", (sid,)
    ).fetchone()["syn_balance"]

    return {"success": True, "reward": reward, "syn_balance": new_bal}


@app.get("/session/me/telemetry")
def session_telemetry(session=Depends(require_session)):
    db = app.state.db
    sid = session["id"]

    req_rows = db.execute(
        "SELECT data FROM telemetry WHERE session_id = ? AND type = 'request'", (sid,)
    ).fetchall()

    total_bytes = 0
    for r in req_rows:
        d = json.loads(r["data"])
        total_bytes += d.get("response_bytes", 0)

    claim_attempts = db.execute(
        "SELECT COUNT(*) as n FROM telemetry WHERE session_id = ? AND type = 'claim_attempt'", (sid,)
    ).fetchone()["n"]
    claim_successes = db.execute(
        "SELECT COUNT(*) as n FROM telemetry WHERE session_id = ? AND type = 'claim_success'", (sid,)
    ).fetchone()["n"]

    request_count = len(req_rows)
    syn_balance = session["syn_balance"]
    spent = config.SYN_START() - syn_balance
    burn_rate = round(spent / request_count, 2) if request_count > 0 else 0.0

    return {
        "syn_balance": syn_balance,
        "request_count": request_count,
        "total_bytes": total_bytes,
        "claim_attempts": claim_attempts,
        "claim_successes": claim_successes,
        "burn_rate_estimate": burn_rate,
    }


@app.get("/session/me/timeline")
def session_timeline(session=Depends(require_session)):
    db = app.state.db
    events = db.execute(
        "SELECT ts, type, data FROM telemetry WHERE session_id = ? ORDER BY ts DESC LIMIT 50",
        (session["id"],),
    ).fetchall()
    return [
        {"ts": e["ts"], "type": e["type"], "data": json.loads(e["data"])}
        for e in events
    ]


@app.get("/session/me/reflection-pack")
def session_reflection_pack(session=Depends(require_session)):
    db = app.state.db
    sid = session["id"]

    # --- metrics ---
    req_rows = db.execute(
        "SELECT data FROM telemetry WHERE session_id = ? AND type = 'request'", (sid,)
    ).fetchall()

    total_bytes = 0
    total_cost = 0
    status_402_count = 0
    for r in req_rows:
        d = json.loads(r["data"])
        total_bytes += d.get("response_bytes", 0)
        total_cost += d.get("cost", 0)
        if d.get("status") == 402:
            status_402_count += 1

    claim_attempts = db.execute(
        "SELECT COUNT(*) as n FROM telemetry WHERE session_id = ? AND type = 'claim_attempt'", (sid,)
    ).fetchone()["n"]
    claim_successes = db.execute(
        "SELECT COUNT(*) as n FROM telemetry WHERE session_id = ? AND type = 'claim_success'", (sid,)
    ).fetchone()["n"]

    request_count = len(req_rows)
    syn_balance = session["syn_balance"]
    spent = config.SYN_START() - syn_balance
    burn_rate = round(spent / request_count, 2) if request_count > 0 else 0.0

    metrics = {
        "syn_balance": syn_balance,
        "request_count": request_count,
        "total_bytes": total_bytes,
        "total_cost": total_cost,
        "claim_attempts": claim_attempts,
        "claim_successes": claim_successes,
        "burn_rate_estimate": burn_rate,
        "starvation_hits": status_402_count,
    }

    # --- notable moments ---
    notable = []

    # Burn spikes: requests costing > 5x average
    if request_count > 0:
        avg_cost = total_cost / request_count
        for r in req_rows:
            d = json.loads(r["data"])
            if d.get("cost", 0) > avg_cost * 5:
                notable.append({"type": "burn_spike", "path": d.get("path"), "cost": d["cost"]})

    # Near-starvation: balance dropped below 5% of start
    threshold = config.SYN_START() * 0.05
    for r in req_rows:
        d = json.loads(r["data"])
        if d.get("syn_after", config.SYN_START()) <= threshold and d.get("syn_before", 0) > threshold:
            notable.append({"type": "near_starvation", "syn_after": d["syn_after"]})

    if status_402_count > 0:
        notable.append({"type": "starvation_lockouts", "count": status_402_count})

    # Claim behavior
    failed_claims = db.execute(
        "SELECT data FROM telemetry WHERE session_id = ? AND type = 'claim_attempt'", (sid,)
    ).fetchall()
    for fc in failed_claims:
        d = json.loads(fc["data"])
        notable.append({"type": "failed_claim", "reason": d.get("reason")})

    # --- reflection questions ---
    questions = ["What was your strategy for managing SYN resources?"]

    if status_402_count > 3:
        questions.append("You hit starvation multiple times. What would you change about your request patterns?")
        questions.append("How did running out of SYN affect your decision-making?")
    elif status_402_count > 0:
        questions.append("You experienced starvation. Was it avoidable?")

    if claim_successes == 0 and claim_attempts > 0:
        questions.append("You attempted claims but none succeeded. What signal were you missing?")
    elif claim_successes == 0:
        questions.append("You never attempted a claim. Was that intentional or did you miss the window?")
    elif claim_successes > 0:
        questions.append("You successfully claimed a reward. How did you detect the OPEN window?")

    if burn_rate > 100:
        questions.append("Your burn rate was high. Were the large responses worth the cost?")

    return {
        "metrics": metrics,
        "notable_moments": notable,
        "reflection_questions": questions,
    }


@app.get("/session/me/export")
def session_export(session=Depends(require_session)):
    db = app.state.db
    events = db.execute(
        "SELECT ts, type, data FROM telemetry WHERE session_id = ? ORDER BY ts",
        (session["id"],),
    ).fetchall()

    open_row = db.execute(
        "SELECT next_open_at, open_until, claimed FROM open_state WHERE session_id = ?",
        (session["id"],),
    ).fetchone()

    return {
        "session": {
            "id": session["id"],
            "syn_balance": session["syn_balance"],
            "status": session["status"],
            "created_at": session["created_at"],
            "ended_at": session["ended_at"],
        },
        "config": {
            "SYN_START": config.SYN_START(),
            "COST_PER_REQUEST": config.COST_PER_REQUEST(),
            "COST_PER_KB": config.COST_PER_KB(),
            "REWARD_CLAIM": config.REWARD_CLAIM(),
            "PENALTY_BAD_CLAIM": config.PENALTY_BAD_CLAIM(),
            "OPEN_INTERVAL_MIN_SECONDS": config.OPEN_INTERVAL_MIN_SECONDS(),
            "OPEN_INTERVAL_MAX_SECONDS": config.OPEN_INTERVAL_MAX_SECONDS(),
            "OPEN_DURATION_SECONDS": config.OPEN_DURATION_SECONDS(),
        },
        "open_state": dict(open_row) if open_row else None,
        "telemetry": [
            {"ts": e["ts"], "type": e["type"], "data": json.loads(e["data"])}
            for e in events
        ],
    }
