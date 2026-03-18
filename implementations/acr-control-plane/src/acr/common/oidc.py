from __future__ import annotations

import json
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import jwt

from acr.common.errors import UnauthorizedOperatorError
from acr.config import oidc_role_mapping, settings

_JWKS_CACHE: dict[str, Any] = {"expires_at": 0.0, "keys": {}}
_JWKS_TTL_SECONDS = 300


@dataclass(frozen=True)
class OIDCPrincipal:
    subject: str
    roles: frozenset[str]
    claims: dict[str, Any]


def oidc_is_enabled() -> bool:
    return settings.oidc_enabled


async def _fetch_jwks() -> dict[str, Any]:
    now = time.time()
    if _JWKS_CACHE["keys"] and _JWKS_CACHE["expires_at"] > now:
        return _JWKS_CACHE["keys"]

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(settings.oidc_jwks_url)
        response.raise_for_status()
        jwks = response.json()
    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
        raise UnauthorizedOperatorError("OIDC JWKS response is invalid")
    _JWKS_CACHE["keys"] = jwks
    _JWKS_CACHE["expires_at"] = now + _JWKS_TTL_SECONDS
    return jwks


async def validate_oidc_token(token: str, *, nonce: str | None = None) -> OIDCPrincipal:
    if not oidc_is_enabled():
        raise UnauthorizedOperatorError("OIDC is not enabled")

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    jwks = await _fetch_jwks()
    key = None
    for item in jwks["keys"]:
        if item.get("kid") == kid:
            key = item
            break
    if key is None:
        raise UnauthorizedOperatorError("OIDC signing key not found")

    claims = jwt.decode(
        token,
        key,
        algorithms=[header.get("alg", "RS256")],
        audience=settings.oidc_client_id,
        issuer=settings.oidc_issuer,
    )
    if nonce is not None and claims.get("nonce") != nonce:
        raise UnauthorizedOperatorError("OIDC nonce validation failed")

    subject_claim = settings.oidc_subject_claim or "email"
    subject = claims.get(subject_claim) or claims.get("sub")
    if not subject:
        raise UnauthorizedOperatorError(f"OIDC token missing subject claim '{subject_claim}'")
    return OIDCPrincipal(
        subject=str(subject),
        roles=_map_oidc_roles(claims),
        claims=dict(claims),
    )


def _extract_claim_values(claims: Mapping[str, Any], claim_name: str) -> list[str]:
    raw = claims.get(claim_name)
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return []


def _map_oidc_roles(claims: Mapping[str, Any]) -> frozenset[str]:
    external_roles = _extract_claim_values(claims, settings.oidc_roles_claim)
    mapping = oidc_role_mapping()
    internal: set[str] = set()
    if mapping:
        for role in external_roles:
            internal.update(mapping.get(role, []))
    else:
        internal.update(external_roles)
    return frozenset(internal)


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.oidc_redirect_uri,
        "client_id": settings.oidc_client_id,
    }
    if settings.oidc_client_secret:
        payload["client_secret"] = settings.oidc_client_secret
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            settings.oidc_token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict) or "id_token" not in data:
        raise UnauthorizedOperatorError("OIDC token response did not include an id_token")
    return data


def create_signed_payload(payload: dict[str, Any], *, ttl_seconds: int) -> str:
    now = int(time.time())
    return jwt.encode(
        {**payload, "iat": now, "exp": now + ttl_seconds},
        settings.operator_session_secret,
        algorithm="HS256",
    )


def decode_signed_payload(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.operator_session_secret,
        algorithms=["HS256"],
    )


def build_oidc_authorize_url(*, state: str, nonce: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_uri,
        "scope": settings.oidc_scopes,
        "state": state,
        "nonce": nonce,
    }
    return f"{settings.oidc_authorize_url}?{urlencode(params)}"


def new_oidc_state() -> tuple[str, str]:
    return secrets.token_urlsafe(24), secrets.token_urlsafe(24)
