from __future__ import annotations

import copy
import hashlib
import hmac
import json
from typing import Any

from acr.config import settings


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def payload_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def remove_integrity_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    stripped = copy.deepcopy(payload)
    metadata = stripped.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("integrity", None)
    return stripped


def sign_payload_hash(payload_hash: str, previous_event_sha256: str | None) -> str:
    message = f"{payload_hash}:{previous_event_sha256 or ''}".encode()
    return hmac.new(
        settings.audit_signing_secret.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()


def extract_payload_hash(payload: dict[str, Any]) -> str | None:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return None
    integrity = metadata.get("integrity")
    if not isinstance(integrity, dict):
        return None
    payload_hash = integrity.get("payload_sha256")
    return str(payload_hash) if payload_hash else None


def verify_event_chain(events: list[dict[str, Any]]) -> dict[str, Any]:
    previous_hash: str | None = None
    verified = 0
    signed = 0
    invalid_reasons: list[str] = []

    for index, event in enumerate(events):
        metadata = event.get("metadata")
        integrity = metadata.get("integrity") if isinstance(metadata, dict) else None
        if not isinstance(integrity, dict):
            invalid_reasons.append(f"event[{index}] missing integrity metadata")
            break

        expected_hash = payload_sha256(remove_integrity_metadata(event))
        actual_hash = integrity.get("payload_sha256")
        if actual_hash != expected_hash:
            invalid_reasons.append(f"event[{index}] payload hash mismatch")
            break

        actual_previous = integrity.get("previous_event_sha256")
        if actual_previous != previous_hash:
            invalid_reasons.append(f"event[{index}] previous-event hash mismatch")
            break

        expected_signature = sign_payload_hash(expected_hash, previous_hash)
        actual_signature = integrity.get("record_signature")
        if not actual_signature or not hmac.compare_digest(
            str(actual_signature), expected_signature
        ):
            invalid_reasons.append(f"event[{index}] record signature mismatch")
            break

        verified += 1
        signed += 1
        previous_hash = expected_hash

    return {
        "chain_valid": not invalid_reasons,
        "verified_events": verified,
        "signed_events": signed,
        "root_event_sha256": previous_hash,
        "invalid_reasons": invalid_reasons,
    }
