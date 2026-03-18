from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.operator_auth import OperatorPrincipal, require_operator_roles
from acr.db.database import get_db
from acr.policy_studio.distribution import build_active_runtime_bundle, build_opa_discovery_document
from acr.policy_studio.models import (
    PolicyPublishRequest,
    PolicyReleaseResponse,
    PolicyBundleResponse,
    PolicyDraftResponse,
    PolicyDraftUpsertRequest,
    PolicySimulationRequest,
    PolicySimulationResponse,
    PolicyValidationResponse,
)
from acr.policy_studio.releases import (
    activate_policy_release,
    list_active_policy_releases,
    list_policy_releases,
    publish_policy_draft,
    rollback_policy_release,
    validate_policy_draft_record,
)
from acr.policy_studio import service
from acr.policy_studio.simulator import simulate_policy_draft

router = APIRouter(prefix="/acr/policy-drafts", tags=["Policy Drafts"])


def _to_response(record) -> PolicyDraftResponse:
    return PolicyDraftResponse.model_validate(record)


def _to_release_response(record) -> PolicyReleaseResponse:
    return PolicyReleaseResponse.model_validate(record)


@router.get("", response_model=list[PolicyDraftResponse])
async def list_drafts(
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "security_admin", "auditor")),
) -> list[PolicyDraftResponse]:
    records = await service.list_policy_drafts(db)
    return [_to_response(record) for record in records]


@router.get("/{draft_id}", response_model=PolicyDraftResponse)
async def get_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "security_admin", "auditor")),
) -> PolicyDraftResponse:
    record = await service.get_policy_draft(db, draft_id)
    return _to_response(record)


@router.post("", response_model=PolicyDraftResponse, status_code=201)
async def create_draft(
    body: PolicyDraftUpsertRequest,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "security_admin")),
) -> PolicyDraftResponse:
    record = await service.create_policy_draft(db, req=body, actor=principal.subject)
    return _to_response(record)


@router.put("/{draft_id}", response_model=PolicyDraftResponse)
async def update_draft(
    draft_id: str,
    body: PolicyDraftUpsertRequest,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "security_admin")),
) -> PolicyDraftResponse:
    record = await service.update_policy_draft(db, draft_id=draft_id, req=body, actor=principal.subject)
    return _to_response(record)


@router.get("/{draft_id}/bundle", response_model=PolicyBundleResponse)
async def get_bundle(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "security_admin", "auditor")),
) -> PolicyBundleResponse:
    record = await service.get_policy_draft(db, draft_id)
    return PolicyBundleResponse(
        draft_id=record.draft_id,
        policy_filename=f"{record.agent_id}.rego",
        manifest_filename=f"{record.agent_id}.manifest.json",
        policy_contents=record.rego_policy,
        manifest=record.manifest,
    )


@router.post("/{draft_id}/simulate", response_model=PolicySimulationResponse)
async def simulate(
    draft_id: str,
    body: PolicySimulationRequest,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "security_admin", "auditor")),
) -> PolicySimulationResponse:
    record = await service.get_policy_draft(db, draft_id)
    return simulate_policy_draft(
        manifest=record.manifest or {},
        wizard_inputs=record.wizard_inputs or {},
        action=body.action,
        context=body.context,
    )


@router.get("/{draft_id}/validate", response_model=PolicyValidationResponse)
async def validate(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "security_admin", "auditor")),
) -> PolicyValidationResponse:
    record = await service.get_policy_draft(db, draft_id)
    return validate_policy_draft_record(record)


@router.post("/{draft_id}/publish", response_model=PolicyReleaseResponse, status_code=201)
async def publish(
    draft_id: str,
    body: PolicyPublishRequest,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("security_admin")),
) -> PolicyReleaseResponse:
    draft = await service.get_policy_draft(db, draft_id)
    record = await publish_policy_draft(db, draft=draft, actor=principal.subject, notes=body.notes)
    return _to_release_response(record)


@router.get("/releases/history", response_model=list[PolicyReleaseResponse])
async def releases(
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("agent_admin", "security_admin", "auditor")),
) -> list[PolicyReleaseResponse]:
    records = await list_policy_releases(db)
    return [_to_release_response(record) for record in records]


@router.get("/../policy-bundles/active.tar.gz", include_in_schema=False)
async def active_bundle_alias() -> Response:
    return Response(status_code=307, headers={"Location": "/acr/policy-bundles/active.tar.gz"})


@router.get("/../policy-bundles/discovery.json", include_in_schema=False)
async def discovery_alias() -> Response:
    return Response(status_code=307, headers={"Location": "/acr/policy-bundles/discovery.json"})


@router.post("/releases/{release_id}/activate", response_model=PolicyReleaseResponse)
async def activate(
    release_id: str,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("security_admin")),
) -> PolicyReleaseResponse:
    record = await activate_policy_release(db, release_id=release_id, actor=principal.subject)
    return _to_release_response(record)


@router.post("/releases/{release_id}/rollback", response_model=PolicyReleaseResponse)
async def rollback(
    release_id: str,
    body: PolicyPublishRequest,
    db: AsyncSession = Depends(get_db),
    principal: OperatorPrincipal = Depends(require_operator_roles("security_admin")),
) -> PolicyReleaseResponse:
    record = await rollback_policy_release(db, release_id=release_id, actor=principal.subject, notes=body.notes)
    return _to_release_response(record)


bundle_router = APIRouter(prefix="/acr/policy-bundles", tags=["Policy Bundles"])


@bundle_router.get("/active.tar.gz")
async def get_active_runtime_bundle(
    db: AsyncSession = Depends(get_db),
) -> Response:
    records = await list_active_policy_releases(db)
    artifact = build_active_runtime_bundle(records)
    return Response(
        content=artifact.bytes_data,
        media_type=artifact.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "X-Policy-Bundle-Sha256": artifact.sha256,
        },
    )


@bundle_router.get("/discovery.json")
async def get_opa_discovery_document(request: Request) -> JSONResponse:
    document = build_opa_discovery_document(service_base_url=str(request.base_url).rstrip("/"))
    return JSONResponse(document)
