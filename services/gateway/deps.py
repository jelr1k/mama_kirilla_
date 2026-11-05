from __future__ import annotations

from typing import Any
from fastapi import Request


def get_gateway(request: Request) -> Any:
    """Dependency provider returning the GatewayService instance bound to the FastAPI app state."""
    return request.app.state.gateway
