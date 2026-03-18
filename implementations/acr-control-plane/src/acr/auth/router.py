from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from acr.common.errors import UnauthorizedOperatorError
from acr.common.oidc import (
    build_oidc_authorize_url,
    create_signed_payload,
    decode_signed_payload,
    exchange_code_for_tokens,
    new_oidc_state,
    oidc_is_enabled,
    validate_oidc_token,
)
from acr.common.operator_auth import OperatorPrincipal, get_operator_principal
from acr.config import settings

router = APIRouter(prefix="/acr/auth", tags=["Operator Auth"])

_STATE_COOKIE = "acr_oidc_state"
_SESSION_COOKIE = "acr_operator_session"


def _session_cookie_settings() -> dict:
    return {
        "httponly": True,
        "secure": settings.acr_env != "development",
        "samesite": "lax",
        "path": "/",
        "max_age": settings.oidc_session_ttl_seconds,
    }


@router.get("/session")
async def session(
    principal: OperatorPrincipal = Depends(get_operator_principal),
) -> dict:
    return {
        "subject": principal.subject,
        "roles": sorted(principal.roles),
        "source": principal.source,
        "key_id": principal.key_id,
    }


@router.get("/oidc/login")
async def oidc_login() -> RedirectResponse:
    if not oidc_is_enabled():
        raise UnauthorizedOperatorError("OIDC is not enabled")
    state, nonce = new_oidc_state()
    encoded = create_signed_payload({"state": state, "nonce": nonce}, ttl_seconds=600)
    response = RedirectResponse(build_oidc_authorize_url(state=state, nonce=nonce), status_code=302)
    response.set_cookie(_STATE_COOKIE, encoded, **_session_cookie_settings())
    return response


@router.get("/oidc/callback")
async def oidc_callback(
    request: Request,
    code: str,
    state: str,
) -> RedirectResponse:
    if not oidc_is_enabled():
        raise UnauthorizedOperatorError("OIDC is not enabled")

    state_cookie = request.cookies.get(_STATE_COOKIE)
    if not state_cookie:
        raise UnauthorizedOperatorError("OIDC state cookie is missing")
    state_payload = decode_signed_payload(state_cookie)
    if state_payload.get("state") != state:
        raise UnauthorizedOperatorError("OIDC state validation failed")

    tokens = await exchange_code_for_tokens(code)
    principal = await validate_oidc_token(tokens["id_token"], nonce=state_payload.get("nonce"))

    session_token = create_signed_payload(
        {
            "subject": principal.subject,
            "roles": sorted(principal.roles),
            "source": "oidc_session",
        },
        ttl_seconds=settings.oidc_session_ttl_seconds,
    )
    response = RedirectResponse("/console", status_code=302)
    response.set_cookie(_SESSION_COOKIE, session_token, **_session_cookie_settings())
    response.delete_cookie(_STATE_COOKIE, path="/")
    return response


@router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie(_SESSION_COOKIE, path="/")
    response.delete_cookie(_STATE_COOKIE, path="/")
    return response
