from __future__ import annotations

import secrets
from dataclasses import dataclass

from fastapi import Depends, Security
from fastapi.security import APIKeyCookie, APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import ForbiddenOperatorError, UnauthorizedOperatorError
from acr.common.oidc import decode_signed_payload, oidc_is_enabled, validate_oidc_token
from acr.db.database import get_db
from acr.config import operator_api_keys
from acr.operator_keys.service import find_operator_key_by_hash, hash_operator_key, touch_operator_key_usage

_bearer_scheme = HTTPBearer(auto_error=False)
_operator_api_key_scheme = APIKeyHeader(name="X-Operator-API-Key", auto_error=False)
_operator_session_scheme = APIKeyCookie(name="acr_operator_session", auto_error=False)


@dataclass(frozen=True)
class OperatorPrincipal:
    subject: str
    roles: frozenset[str]
    source: str = "bootstrap"
    key_id: str | None = None


async def get_operator_principal(
    authorization: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
    x_operator_api_key: str | None = Security(_operator_api_key_scheme),
    acr_operator_session: str | None = Security(_operator_session_scheme),
    db: AsyncSession = Depends(get_db),
) -> OperatorPrincipal:
    if authorization and authorization.scheme.lower() == "bearer":
        principal = await validate_oidc_token(authorization.credentials)
        return OperatorPrincipal(
            subject=principal.subject,
            roles=principal.roles,
            source="oidc_bearer",
        )

    if acr_operator_session:
        try:
            session_payload = decode_signed_payload(acr_operator_session)
        except Exception as exc:
            raise UnauthorizedOperatorError("Operator session is invalid") from exc
        return OperatorPrincipal(
            subject=str(session_payload.get("subject") or "operator"),
            roles=frozenset(str(role) for role in (session_payload.get("roles") or [])),
            source=str(session_payload.get("source") or "oidc_session"),
        )

    if not x_operator_api_key:
        if oidc_is_enabled():
            raise UnauthorizedOperatorError(
                "Operator authentication required via OIDC session, Bearer token, or X-Operator-API-Key"
            )
        raise UnauthorizedOperatorError("X-Operator-API-Key header is required")

    db_record = await find_operator_key_by_hash(db, hash_operator_key(x_operator_api_key))
    if db_record is not None:
        await touch_operator_key_usage(db, db_record)
        return OperatorPrincipal(
            subject=db_record.subject,
            roles=frozenset(str(role) for role in (db_record.roles or [])),
            source="database",
            key_id=db_record.key_id,
        )

    for expected_key, identity in operator_api_keys().items():
        if secrets.compare_digest(x_operator_api_key, expected_key):
            subject = str(identity.get("subject") or "operator")
            roles = identity.get("roles") or []
            if not isinstance(roles, list):
                raise UnauthorizedOperatorError("Operator roles configuration is invalid")
            return OperatorPrincipal(
                subject=subject,
                roles=frozenset(str(r) for r in roles),
                source="bootstrap",
            )

    raise UnauthorizedOperatorError("Operator API key is invalid")


def require_operator_roles(*required_roles: str):
    async def _dependency(
        principal: OperatorPrincipal = Depends(get_operator_principal),
    ) -> OperatorPrincipal:
        if required_roles and principal.roles.isdisjoint(required_roles):
            raise ForbiddenOperatorError(
                f"Operator '{principal.subject}' lacks one of the required roles: "
                f"{', '.join(required_roles)}"
            )
        return principal

    return _dependency
