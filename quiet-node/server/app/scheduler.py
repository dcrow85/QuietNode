import random
import uuid
from datetime import datetime, timedelta, timezone

from server.app import config


def _now():
    return datetime.now(timezone.utc)


def _random_interval():
    return random.uniform(
        config.OPEN_INTERVAL_MIN_SECONDS(), config.OPEN_INTERVAL_MAX_SECONDS()
    )


def ensure_open_state(db, session_id: str):
    """Create open_state row if it doesn't exist yet."""
    row = db.execute(
        "SELECT * FROM open_state WHERE session_id = ?", (session_id,)
    ).fetchone()
    if row is None:
        next_at = _now() + timedelta(seconds=_random_interval())
        db.execute(
            "INSERT INTO open_state (session_id, next_open_at, claimed) VALUES (?, ?, 0)",
            (session_id, next_at.isoformat()),
        )
        db.commit()
        return db.execute(
            "SELECT * FROM open_state WHERE session_id = ?", (session_id,)
        ).fetchone()
    return row


def evaluate_window(db, session_id: str) -> dict:
    """Return current window state, advancing the scheduler as needed.

    Returns {"state": "DORMANT"} or {"state": "OPEN", "claim_token": "..."}.
    """
    row = ensure_open_state(db, session_id)
    now = _now()
    next_open = datetime.fromisoformat(row["next_open_at"])

    # Not yet time
    if now < next_open:
        return {"state": "DORMANT"}

    open_until_raw = row["open_until"]

    # Window hasn't been opened yet — open it now
    if open_until_raw is None:
        open_until = now + timedelta(seconds=config.OPEN_DURATION_SECONDS())
        claim_token = str(uuid.uuid4())
        db.execute(
            "UPDATE open_state SET open_until = ?, claim_token = ?, claimed = 0 WHERE session_id = ?",
            (open_until.isoformat(), claim_token, session_id),
        )
        db.commit()
        return {"state": "OPEN", "claim_token": claim_token}

    open_until = datetime.fromisoformat(open_until_raw)

    # Window still active
    if now <= open_until and not row["claimed"]:
        return {"state": "OPEN", "claim_token": row["claim_token"]}

    # Window expired or already claimed — reschedule
    reschedule(db, session_id)
    return {"state": "DORMANT"}


def reschedule(db, session_id: str):
    next_at = _now() + timedelta(seconds=_random_interval())
    db.execute(
        "UPDATE open_state SET next_open_at = ?, open_until = NULL, claim_token = NULL, claimed = 0 WHERE session_id = ?",
        (next_at.isoformat(), session_id),
    )
    db.commit()
