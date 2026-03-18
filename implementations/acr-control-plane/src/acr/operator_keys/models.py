from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OperatorKeyCreateRequest(BaseModel):
    name: str
    subject: str
    roles: list[str] = Field(default_factory=list)


class OperatorKeyRotateRequest(BaseModel):
    reason: str | None = None


class OperatorKeyResponse(BaseModel):
    key_id: str
    name: str
    subject: str
    roles: list[str]
    is_active: bool
    created_by: str | None
    revoked_by: str | None
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class OperatorKeyCreateResponse(OperatorKeyResponse):
    api_key: str
