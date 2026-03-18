from __future__ import annotations

import hashlib
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from acr.common.errors import OperatorCredentialNotFoundError
from acr.common.time import utcnow
from acr.db.models import OperatorCredentialRecord
from acr.operator_keys.models import OperatorKeyCreateRequest


def hash_operator_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_operator_api_key() -> str:
    return f"acr_op_{secrets.token_urlsafe(24)}"


async def create_operator_key(
    db: AsyncSession,
    *,
    req: OperatorKeyCreateRequest,
    created_by: str,
) -> tuple[OperatorCredentialRecord, str]:
    api_key = generate_operator_api_key()
    record = OperatorCredentialRecord(
        key_id=f"opk-{uuid.uuid4()}",
        name=req.name,
        subject=req.subject,
        key_hash=hash_operator_key(api_key),
        roles=req.roles,
        is_active=True,
        created_by=created_by,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record, api_key


async def list_operator_keys(db: AsyncSession) -> list[OperatorCredentialRecord]:
    result = await db.execute(
        select(OperatorCredentialRecord).order_by(OperatorCredentialRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def get_operator_key(db: AsyncSession, key_id: str) -> OperatorCredentialRecord:
    result = await db.execute(
        select(OperatorCredentialRecord).where(OperatorCredentialRecord.key_id == key_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise OperatorCredentialNotFoundError(f"Operator key '{key_id}' not found")
    return record


async def revoke_operator_key(
    db: AsyncSession,
    *,
    key_id: str,
    revoked_by: str,
) -> OperatorCredentialRecord:
    record = await get_operator_key(db, key_id)
    record.is_active = False
    record.revoked_by = revoked_by
    record.revoked_at = utcnow()
    await db.flush()
    await db.refresh(record)
    return record


async def rotate_operator_key(
    db: AsyncSession,
    *,
    key_id: str,
    rotated_by: str,
) -> tuple[OperatorCredentialRecord, str]:
    record = await get_operator_key(db, key_id)
    new_api_key = generate_operator_api_key()
    record.key_hash = hash_operator_key(new_api_key)
    record.revoked_by = None
    record.revoked_at = None
    record.is_active = True
    record.last_used_at = None
    await db.flush()
    await db.refresh(record)
    return record, new_api_key


async def find_operator_key_by_hash(
    db: AsyncSession,
    key_hash: str,
) -> OperatorCredentialRecord | None:
    result = await db.execute(
        select(OperatorCredentialRecord).where(
            OperatorCredentialRecord.key_hash == key_hash,
            OperatorCredentialRecord.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def touch_operator_key_usage(db: AsyncSession, record: OperatorCredentialRecord) -> None:
    record.last_used_at = utcnow()
    await db.flush()
