from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.oidc import create_signed_payload, decode_signed_payload
from acr.common.operator_auth import get_operator_principal
from acr.config import settings
from acr.operator_keys.models import OperatorKeyCreateRequest
from acr.operator_keys.service import create_operator_key


class TestOperatorKeyAPI:
    async def test_create_and_list_operator_keys(
        self, async_client: AsyncClient
    ) -> None:
        create_resp = await async_client.post(
            "/acr/operator-keys",
            json={
                "name": "Security Admin",
                "subject": "security@example.com",
                "roles": ["security_admin", "auditor"],
            },
        )
        assert create_resp.status_code == 201
        payload = create_resp.json()
        assert payload["api_key"].startswith("acr_op_")
        assert payload["subject"] == "security@example.com"

        list_resp = await async_client.get("/acr/operator-keys")
        assert list_resp.status_code == 200
        keys = list_resp.json()
        assert any(item["key_id"] == payload["key_id"] for item in keys)

    async def test_rotate_and_revoke_operator_key(self, async_client: AsyncClient) -> None:
        create_resp = await async_client.post(
            "/acr/operator-keys",
            json={
                "name": "Finance Approver",
                "subject": "finance@example.com",
                "roles": ["approver"],
            },
        )
        key_id = create_resp.json()["key_id"]

        rotate_resp = await async_client.post(f"/acr/operator-keys/{key_id}/rotate")
        assert rotate_resp.status_code == 200
        assert rotate_resp.json()["api_key"].startswith("acr_op_")

        revoke_resp = await async_client.post(f"/acr/operator-keys/{key_id}/revoke")
        assert revoke_resp.status_code == 200
        assert revoke_resp.json()["is_active"] is False


class TestDatabaseOperatorAuth:
    async def test_database_operator_key_authenticates(
        self, db: AsyncSession
    ) -> None:
        record, api_key = await create_operator_key(
            db,
            req=OperatorKeyCreateRequest(
                name="Platform Admin",
                subject="platform@example.com",
                roles=["agent_admin", "security_admin"],
            ),
            created_by="bootstrap-admin",
        )
        await db.commit()

        principal = await get_operator_principal(
            authorization=None,
            x_operator_api_key=api_key,
            acr_operator_session=None,
            db=db,
        )
        assert principal.subject == "platform@example.com"
        assert principal.source == "database"
        assert principal.key_id == record.key_id

    async def test_signed_operator_session_authenticates(self, db: AsyncSession) -> None:
        token = create_signed_payload(
            {
                "subject": "oidc-user@example.com",
                "roles": ["security_admin", "auditor"],
                "source": "oidc_session",
            },
            ttl_seconds=600,
        )

        principal = await get_operator_principal(
            authorization=None,
            x_operator_api_key=None,
            acr_operator_session=token,
            db=db,
        )

        assert principal.subject == "oidc-user@example.com"
        assert principal.source == "oidc_session"
        assert "security_admin" in principal.roles


class TestOIDCAuthAPI:
    async def test_oidc_login_redirects(self, async_client: AsyncClient, monkeypatch) -> None:
        monkeypatch.setattr(settings, "oidc_enabled", True)
        monkeypatch.setattr(settings, "oidc_client_id", "client-123")
        monkeypatch.setattr(settings, "oidc_redirect_uri", "http://test/acr/auth/oidc/callback")
        monkeypatch.setattr(settings, "oidc_scopes", "openid profile email")
        monkeypatch.setattr(settings, "oidc_authorize_url", "https://issuer.example.com/authorize")

        response = await async_client.get("/acr/auth/oidc/login", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"].startswith("https://issuer.example.com/authorize")
        assert "acr_oidc_state=" in response.headers["set-cookie"]

    async def test_oidc_callback_sets_session_cookie(self, async_client: AsyncClient, monkeypatch) -> None:
        monkeypatch.setattr(settings, "oidc_enabled", True)
        monkeypatch.setattr(settings, "oidc_client_id", "client-123")
        monkeypatch.setattr(settings, "oidc_redirect_uri", "http://test/acr/auth/oidc/callback")
        monkeypatch.setattr(settings, "oidc_scopes", "openid profile email")
        monkeypatch.setattr(settings, "oidc_authorize_url", "https://issuer.example.com/authorize")
        monkeypatch.setattr(settings, "oidc_session_ttl_seconds", 600)

        login_response = await async_client.get("/acr/auth/oidc/login", follow_redirects=False)
        state_cookie = login_response.cookies.get("acr_oidc_state")
        state_payload = decode_signed_payload(state_cookie)

        with (
            patch(
                "acr.auth.router.exchange_code_for_tokens",
                new_callable=AsyncMock,
                return_value={"id_token": "test-id-token"},
            ),
            patch(
                "acr.auth.router.validate_oidc_token",
                new_callable=AsyncMock,
                return_value=type(
                    "OIDCPrincipalStub",
                    (),
                    {"subject": "sso@example.com", "roles": frozenset({"security_admin"})},
                )(),
            ),
        ):
            callback_response = await async_client.get(
                "/acr/auth/oidc/callback?code=test-code&state="
                + state_payload["state"],
                cookies={"acr_oidc_state": state_cookie},
                follow_redirects=False,
            )

        assert callback_response.status_code == 302
        assert callback_response.headers["location"] == "/console"
        assert "acr_operator_session=" in callback_response.headers["set-cookie"]
