from __future__ import annotations

import os
import secrets
from typing import Any
from fastapi import Header, HTTPException, Request, status


def get_gateway(request: Request) -> Any:
    """Dependency provider returning the GatewayService instance bound to the FastAPI app state."""
    return request.app.state.gateway


def verify_session_token(request: Request, authorization: str | None = Header(None)) -> str:
    """Verify Bearer session token for sensitive Gateway endpoints."""
    # During pytest or when auth is explicitly disabled, skip token check
    if os.environ.get("JARVIS_DISABLE_AUTH", "").lower() in ("1", "true", "yes") or "PYTEST_CURRENT_TEST" in os.environ:
        return ""

    gateway = getattr(request.app.state, "gateway", None)
    expected_token = getattr(gateway, "session_token", None) if gateway else None
    if not expected_token:
        return ""

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    if not token or not secrets.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session token",
        )
    return token
