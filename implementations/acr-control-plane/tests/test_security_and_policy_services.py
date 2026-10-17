from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import (
    PolicyDraftNotFoundError,
    PolicyReleaseNotFoundError,
    PolicyValidationError,
    UnauthorizedOperatorError,
)
from acr.common.oidc import (
    _JWKS_CACHE,
    _extract_claim_values,
    _fetch_jwks,
    _map_oidc_roles,
    build_oidc_authorize_url,
    create_signed_payload,
    decode_signed_payload,
    exchange_code_for_tokens,
    new_oidc_state,
    oidc_is_enabled,
    validate_oidc_token,
)
from acr.config import oidc_role_mapping, settings
from acr.db.models import PolicyReleaseRecord
from acr.gateway.spend_control import adjust_authoritative_spend, get_authoritative_projected_spend
from acr.policy_studio.models import PolicyDraftUpsertRequest
from acr.policy_studio.releases import (
    activate_policy_release,
    get_policy_release,
    list_active_policy_releases,
    list_policy_releases,
    publish_policy_draft,
    rollback_policy_release,
    validate_policy_draft_record,
)
from acr.policy_studio.service import (
    create_policy_draft,
    get_policy_draft,
    list_policy_drafts,
    update_policy_draft,
)


@pytest.fixture(autouse=True)
def _reset_oidc_cache() -> None:
    _JWKS_CACHE["expires_at"] = 0.0
    _JWKS_CACHE["keys"] = {}
    oidc_role_mapping.cache_clear()


class TestOIDCHelpers:
    def test_oidc_is_enabled_reflects_settings(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "oidc_enabled", True)
        assert oidc_is_enabled() is True
        monkeypatch.setattr(settings, "oidc_enabled", False)
        assert oidc_is_enabled() is False

    def test_extract_claim_values_handles_scalar_list_and_missing(self) -> None:
        assert _extract_claim_values({"roles": "admin"}, "roles") == ["admin"]
        assert _extract_claim_values({"roles": ["admin", 2]}, "roles") == ["admin", "2"]
        assert _extract_claim_values({}, "roles") == []

    def test_map_oidc_roles_uses_mapping_or_falls_back(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "oidc_roles_claim", "groups")
        monkeypatch.setattr(
            settings, "oidc_role_mapping_json", '{"grp-admin":["security_admin","auditor"]}'
        )
        oidc_role_mapping.cache_clear()
        assert _map_oidc_roles({"groups": ["grp-admin"]}) == frozenset(
            {"security_admin", "auditor"}
        )

        monkeypatch.setattr(settings, "oidc_role_mapping_json", "")
        oidc_role_mapping.cache_clear()
        assert _map_oidc_roles({"groups": ["plain-role"]}) == frozenset({"plain-role"})

    def test_signed_payload_round_trip(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "operator_session_secret", "s" * 64)
        token = create_signed_payload({"subject": "alice", "roles": ["auditor"]}, ttl_seconds=60)
        claims = decode_signed_payload(token)
        assert claims["subject"] == "alice"
        assert claims["roles"] == ["auditor"]

    def test_build_oidc_authorize_url_and_state(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "oidc_client_id", "client-123")
        monkeypatch.setattr(settings, "oidc_redirect_uri", "https://example.com/callback")
        monkeypatch.setattr(settings, "oidc_scopes", "openid email")
        monkeypatch.setattr(settings, "oidc_authorize_url", "https://idp.example.com/authorize")
        state, nonce = new_oidc_state()
        url = build_oidc_authorize_url(state=state, nonce=nonce)
        assert "client_id=client-123" in url
        assert "state=" in url
        assert "nonce=" in url
        assert state and nonce and state != nonce

    async def test_fetch_jwks_caches_successful_response(self, monkeypatch) -> None:
        response = MagicMock()
        response.json.return_value = {"keys": [{"kid": "k1"}]}
        response.raise_for_status = MagicMock()
        client = AsyncMock()
        client.get = AsyncMock(return_value=response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("acr.common.oidc.httpx.AsyncClient", return_value=client):
            first = await _fetch_jwks()
            second = await _fetch_jwks()

        assert first == second
        assert client.get.await_count == 1

    async def test_fetch_jwks_rejects_invalid_shape(self) -> None:
        response = MagicMock()
        response.json.return_value = {"unexpected": True}
        response.raise_for_status = MagicMock()
        client = AsyncMock()
        client.get = AsyncMock(return_value=response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("acr.common.oidc.httpx.AsyncClient", return_value=client),
            pytest.raises(UnauthorizedOperatorError, match="JWKS response is invalid"),
        ):
            await _fetch_jwks()

    async def test_validate_oidc_token_success_and_nonce_check(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "oidc_enabled", True)
        monkeypatch.setattr(settings, "oidc_client_id", "client-123")
        monkeypatch.setattr(settings, "oidc_issuer", "https://idp.example.com")
        monkeypatch.setattr(settings, "oidc_subject_claim", "email")
        monkeypatch.setattr(settings, "oidc_roles_claim", "groups")
        monkeypatch.setattr(settings, "oidc_role_mapping_json", '{"grp-admin":["security_admin"]}')
        oidc_role_mapping.cache_clear()

        with (
            patch(
                "acr.common.oidc._fetch_jwks",
                new_callable=AsyncMock,
                return_value={"keys": [{"kid": "kid-1"}]},
            ),
            patch("acr.common.oidc.jwt.get_unverified_header", return_value={"kid": "kid-1"}),
            patch("acr.common.oidc.jwt.PyJWK.from_dict"),
            patch(
                "acr.common.oidc.jwt.decode",
                return_value={
                    "email": "alice@example.com",
                    "groups": ["grp-admin"],
                    "nonce": "n-123",
                },
            ),
        ):
            principal = await validate_oidc_token("token-123", nonce="n-123")

        assert principal.subject == "alice@example.com"
        assert principal.roles == frozenset({"security_admin"})

    async def test_validate_oidc_token_rejects_missing_key_or_nonce(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "oidc_enabled", True)
        with (
            patch("acr.common.oidc._fetch_jwks", new_callable=AsyncMock, return_value={"keys": []}),
            patch("acr.common.oidc.jwt.get_unverified_header", return_value={"kid": "missing"}),
            pytest.raises(UnauthorizedOperatorError, match="signing key not found"),
        ):
            await validate_oidc_token("token-123")

        with (
            patch(
                "acr.common.oidc._fetch_jwks",
                new_callable=AsyncMock,
                return_value={"keys": [{"kid": "kid-1"}]},
            ),
            patch("acr.common.oidc.jwt.get_unverified_header", return_value={"kid": "kid-1"}),
            patch("acr.common.oidc.jwt.PyJWK.from_dict"),
            patch("acr.common.oidc.jwt.decode", return_value={"sub": "alice", "nonce": "bad"}),
            pytest.raises(UnauthorizedOperatorError, match="nonce validation failed"),
        ):
            await validate_oidc_token("token-123", nonce="expected")

    async def test_exchange_code_for_tokens_success_and_missing_id_token(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "oidc_redirect_uri", "https://example.com/callback")
        monkeypatch.setattr(settings, "oidc_client_id", "client-123")
        monkeypatch.setattr(settings, "oidc_client_secret", "secret-123")
        monkeypatch.setattr(settings, "oidc_token_url", "https://idp.example.com/token")

        good_response = MagicMock()
        good_response.raise_for_status = MagicMock()
        good_response.json.return_value = {"id_token": "jwt", "access_token": "access"}

        bad_response = MagicMock()
        bad_response.raise_for_status = MagicMock()
        bad_response.json.return_value = {"access_token": "access"}

        client = AsyncMock()
        client.post = AsyncMock(side_effect=[good_response, bad_response])
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("acr.common.oidc.httpx.AsyncClient", return_value=client):
            tokens = await exchange_code_for_tokens("code-1")
            assert tokens["id_token"] == "jwt"
            with pytest.raises(UnauthorizedOperatorError, match="did not include an id_token"):
                await exchange_code_for_tokens("code-2")


class TestSpendControlEdges:
    async def test_projected_spend_and_adjust_use_redis_when_available(self) -> None:
        redis = AsyncMock()
        redis.get = AsyncMock(return_value="1.25")
        redis.incrbyfloat = AsyncMock()
        redis.expire = AsyncMock()

        with patch("acr.gateway.spend_control.get_redis_or_none", return_value=redis):
            projected = await get_authoritative_projected_spend("agent-1", 0.5)
            await adjust_authoritative_spend("agent-1", 0.5)

        assert projected == 1.75
        redis.incrbyfloat.assert_awaited()
        redis.expire.assert_awaited()


class TestPolicyDraftServices:
    async def test_create_list_get_and_update_policy_draft_directly(self, db: AsyncSession) -> None:
        req = PolicyDraftUpsertRequest(
            name="Draft One",
            agent_id="agent-1",
            template="customer_support",
            manifest={
                "agent_id": "agent-1",
                "purpose": "Help customers",
                "allowed_tools": ["query_customer_db"],
            },
            rego_policy="package acr\nallow if true",
            wizard_inputs={"template": "customer_support"},
        )
        record = await create_policy_draft(db, req=req, actor="alice")
        drafts = await list_policy_drafts(db)
        fetched = await get_policy_draft(db, record.draft_id)

        assert drafts[0].draft_id == record.draft_id
        assert fetched.created_by == "alice"

        updated = await update_policy_draft(
            db,
            draft_id=record.draft_id,
            req=req.model_copy(update={"name": "Draft Two"}),
            actor="bob",
        )
        assert updated.name == "Draft Two"
        assert updated.updated_by == "bob"

        with pytest.raises(PolicyDraftNotFoundError):
            await get_policy_draft(db, "pdr-missing")


class TestPolicyReleaseServices:
    async def test_validate_policy_draft_record_catches_issues_and_warnings(
        self, db: AsyncSession
    ) -> None:
        draft = await create_policy_draft(
            db,
            req=PolicyDraftUpsertRequest(
                name="Bad Draft",
                agent_id="agent-2",
                template="customer_support",
                manifest={"agent_id": "", "purpose": "", "risk_tier": "high", "allowed_tools": []},
                rego_policy="",
                wizard_inputs={"escalate_tool": "issue_refund"},
            ),
            actor="alice",
        )
        validation = validate_policy_draft_record(draft)
        assert validation.valid is False
        assert validation.issues
        assert validation.warnings

    async def test_publish_activate_and_rollback_policy_release(self, db: AsyncSession) -> None:
        req = PolicyDraftUpsertRequest(
            name="Good Draft",
            agent_id="agent-3",
            template="customer_support",
            manifest={
                "agent_id": "agent-3",
                "purpose": "Help customers",
                "allowed_tools": ["query_customer_db"],
            },
            rego_policy="package acr\nallow if true",
            wizard_inputs={"template": "customer_support"},
        )
        draft = await create_policy_draft(db, req=req, actor="alice")

        published_artifact = SimpleNamespace(
            uri="s3://bundle-1.tar.gz", sha256="abc123", backend="s3"
        )
        active_artifact = SimpleNamespace(uri="s3://active-bundle.tar.gz")

        with (
            patch("acr.policy_studio.releases.build_policy_bundle", return_value=b"bundle-bytes"),
            patch(
                "acr.policy_studio.releases.publish_policy_bundle", return_value=published_artifact
            ),
            patch(
                "acr.policy_studio.releases.publish_active_policy_bundle",
                return_value=active_artifact,
            ),
        ):
            release = await publish_policy_draft(
                db, draft=draft, actor="alice", notes="first publish"
            )
            await db.commit()
            activated = await activate_policy_release(
                db, release_id=release.release_id, actor="bob"
            )
            await db.commit()
            rolled_back = await rollback_policy_release(
                db, release_id=release.release_id, actor="carol"
            )

        releases = await list_policy_releases(db)
        active_releases = await list_active_policy_releases(db)
        assert release.artifact_uri == "s3://bundle-1.tar.gz"
        assert activated.active_bundle_uri == "s3://active-bundle.tar.gz"
        assert any(item.release_id == rolled_back.release_id for item in releases)
        assert any(item.release_id == activated.release_id for item in active_releases)
        assert rolled_back.rollback_from_release_id == release.release_id

    async def test_publish_rejects_invalid_policy_and_release_lookup_not_found(
        self, db: AsyncSession
    ) -> None:
        invalid_draft = await create_policy_draft(
            db,
            req=PolicyDraftUpsertRequest(
                name="Invalid Draft",
                agent_id="agent-4",
                template="customer_support",
                manifest={"agent_id": "agent-4", "purpose": "Missing tools"},
                rego_policy="package acr",
                wizard_inputs={},
            ),
            actor="alice",
        )

        with pytest.raises(PolicyValidationError):
            await publish_policy_draft(db, draft=invalid_draft, actor="alice")

        with pytest.raises(PolicyReleaseNotFoundError):
            await get_policy_release(db, "prl-missing")

    async def test_activate_policy_release_deactivates_previous_active_release(
        self, db: AsyncSession
    ) -> None:
        previous = PolicyReleaseRecord(
            release_id="prl-old",
            draft_id="pdr-old",
            agent_id="agent-5",
            version=1,
            name="Old Release",
            template="customer_support",
            manifest={
                "agent_id": "agent-5",
                "purpose": "Help customers",
                "allowed_tools": ["query_customer_db"],
            },
            rego_policy="package acr\nallow if true",
            status="published",
            activation_status="active",
            active_bundle_uri="s3://old-active.tar.gz",
            activated_by="alice",
        )
        current = PolicyReleaseRecord(
            release_id="prl-new",
            draft_id="pdr-new",
            agent_id="agent-5",
            version=2,
            name="New Release",
            template="customer_support",
            manifest={
                "agent_id": "agent-5",
                "purpose": "Help customers",
                "allowed_tools": ["query_customer_db"],
            },
            rego_policy="package acr\nallow if true",
            status="published",
            activation_status="inactive",
        )
        db.add(previous)
        db.add(current)
        await db.flush()

        with (
            patch("acr.policy_studio.releases.build_policy_bundle", return_value=b"bundle-bytes"),
            patch(
                "acr.policy_studio.releases.publish_active_policy_bundle",
                return_value=SimpleNamespace(uri="s3://new-active.tar.gz"),
            ),
        ):
            activated = await activate_policy_release(db, release_id="prl-new", actor="bob")

        assert activated.activation_status == "active"
        assert previous.activation_status == "inactive"
        assert previous.active_bundle_uri is None
