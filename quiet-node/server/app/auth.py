import hashlib
import sqlite3

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.app.db import get_connection

bearer_scheme = HTTPBearer()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


def require_session(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: sqlite3.Connection = Depends(get_db),
) -> sqlite3.Row:
    token_h = hash_token(creds.credentials)
    row = db.execute(
        "SELECT * FROM sessions WHERE token_hash = ?", (token_h,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid session token")
    return row
