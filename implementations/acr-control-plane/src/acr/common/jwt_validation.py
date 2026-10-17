"""JWT claim checks shared by agent, operator, and execution authentication."""

from __future__ import annotations

from typing import Any

import jwt


def decode_jwt(
    token: str,
    key: Any,
    *,
    algorithms: list[str],
    audience: str | None = None,
    issuer: str | None = None,
) -> dict[str, Any]:
    claims = jwt.decode(token, key, algorithms=algorithms, audience=audience, issuer=issuer)
    # python-jose rejected even an empty audience when no audience was expected.
    # PyJWT otherwise accepts an empty aud as though the claim were absent.
    if audience is None and "aud" in claims:
        raise jwt.InvalidAudienceError("Invalid audience")
    # None of our authentication paths receives the access token needed to
    # validate at_hash. Preserve python-jose's fail-closed behavior rather than
    # silently accepting a claim that PyJWT does not verify itself.
    if "at_hash" in claims:
        raise jwt.InvalidTokenError("No access token provided to verify at_hash claim")
    return claims
