import json
from datetime import datetime, timezone


def log_event(db, session_id: str, event_type: str, data: dict):
    db.execute(
        "INSERT INTO telemetry (session_id, ts, type, data) VALUES (?, ?, ?, ?)",
        (session_id, datetime.now(timezone.utc).isoformat(), event_type, json.dumps(data)),
    )
    db.commit()
