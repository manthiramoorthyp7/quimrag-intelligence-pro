"""Optional API-key auth. OFF by default for the local/single-machine target
(ARCHITECTURE_DECISIONS.md #6) -- set QUIMRAG_API_KEY to turn it on. This is
intentionally NOT a full RBAC/multi-tenant system; it is the minimum step up
from "no auth at all" for anyone running the API reachable beyond localhost."""
from fastapi import Header, HTTPException, status

from . import config


async def require_api_key(authorization: str | None = Header(default=None)):
    if not config.AUTH_ENABLED:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if token != config.API_KEY:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
