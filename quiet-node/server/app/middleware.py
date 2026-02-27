import math

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from server.app import config
from server.app.auth import hash_token
from server.app.telemetry import log_event

# Paths exempt from metering and starvation gate
EXEMPT_PATHS = {"/health", "/session/new", "/docs", "/openapi.json"}
# Paths accessible even when starved (beyond EXEMPT_PATHS)
STARVED_ALLOWED = {"/session/me/export"}


def _resolve_session(request: Request):
    """Look up session from Bearer token without raising."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    db = request.app.state.db
    token_h = hash_token(token)
    return db.execute(
        "SELECT * FROM sessions WHERE token_hash = ?", (token_h,)
    ).fetchone()


class MeteringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Exempt paths pass through with no metering
        if path in EXEMPT_PATHS:
            return await call_next(request)

        session = _resolve_session(request)

        # No session means auth will fail downstream — let it through
        if session is None:
            return await call_next(request)

        # Starvation gate
        if session["syn_balance"] <= 0 and path not in STARVED_ALLOWED:
            log_event(request.app.state.db, session["id"], "request", {
                "path": path,
                "method": request.method,
                "status": 402,
                "response_bytes": 0,
                "cost": 0,
                "syn_before": session["syn_balance"],
                "syn_after": session["syn_balance"],
            })
            return JSONResponse(
                status_code=402,
                content={"detail": "SYN balance exhausted"},
            )

        # Call endpoint
        response = await call_next(request)

        # Read response body to measure size
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        response_bytes = len(body)

        # Compute cost
        cost = config.COST_PER_REQUEST() + config.COST_PER_KB() * math.ceil(response_bytes / 1024)

        # Debit
        db = request.app.state.db
        syn_before = session["syn_balance"]
        syn_after = syn_before - cost
        db.execute(
            "UPDATE sessions SET syn_balance = ?, status = CASE WHEN ? <= 0 THEN 'STARVED' ELSE status END WHERE id = ?",
            (syn_after, syn_after, session["id"]),
        )
        db.commit()

        # Log telemetry
        log_event(db, session["id"], "request", {
            "path": path,
            "method": request.method,
            "status": response.status_code,
            "response_bytes": response_bytes,
            "cost": cost,
            "syn_before": syn_before,
            "syn_after": syn_after,
        })

        # Return response with measured body
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
