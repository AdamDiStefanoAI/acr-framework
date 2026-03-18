"""
Gateway authentication: JWT Bearer token validation dependency.

Every request to POST /acr/evaluate must carry a valid JWT issued by
the ACR control plane's own token endpoint (POST /acr/agents/{id}/token).
The token's `sub` claim is the agent_id; the router verifies it matches
the agent_id in the request body.
"""
from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from acr.common.errors import InvalidTokenError
from acr.pillar1_identity.validator import decode_token

_bearer = HTTPBearer(auto_error=False)


async def require_agent_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """
    FastAPI dependency that validates a Bearer JWT and returns the agent_id.

    Raises:
        InvalidTokenError (401) — if the Authorization header is missing or the token is invalid.
        TokenExpiredError (401)  — if the token has expired.
    """
    if credentials is None:
        raise InvalidTokenError("Authorization header with Bearer token is required")
    # decode_token raises InvalidTokenError or TokenExpiredError on failure
    return decode_token(credentials.credentials)
