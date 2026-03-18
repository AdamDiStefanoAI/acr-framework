from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PolicyDraftUpsertRequest(BaseModel):
    name: str
    agent_id: str
    template: str
    manifest: dict = Field(default_factory=dict)
    rego_policy: str
    wizard_inputs: dict = Field(default_factory=dict)


class PolicyDraftResponse(BaseModel):
    draft_id: str
    name: str
    agent_id: str
    template: str
    manifest: dict
    rego_policy: str
    wizard_inputs: dict
    created_by: str | None
    updated_by: str | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class PolicySimulationRequest(BaseModel):
    action: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)


class PolicySimulationResponse(BaseModel):
    final_decision: str
    reasons: list[str] = Field(default_factory=list)
    approval_queue: str | None = None
    matched_rules: list[str] = Field(default_factory=list)
    manifest_summary: dict = Field(default_factory=dict)


class PolicyBundleResponse(BaseModel):
    draft_id: str
    policy_filename: str
    manifest_filename: str
    policy_contents: str
    manifest: dict


class PolicyValidationResponse(BaseModel):
    valid: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PolicyPublishRequest(BaseModel):
    notes: str | None = None


class PolicyReleaseResponse(BaseModel):
    release_id: str
    draft_id: str
    agent_id: str
    version: int
    name: str
    template: str
    status: str
    activation_status: str
    artifact_uri: str | None
    active_bundle_uri: str | None
    artifact_sha256: str | None
    publish_backend: str | None
    activated_by: str | None
    activated_at: datetime | None
    published_by: str | None
    rollback_from_release_id: str | None
    notes: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}
