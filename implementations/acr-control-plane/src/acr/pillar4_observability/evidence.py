from __future__ import annotations

import hashlib
import hmac
import io
import json
import zipfile
from dataclasses import dataclass

from acr.common.errors import EvidenceBundleNotFoundError
from acr.common.time import iso_utcnow
from acr.config import settings
from acr.pillar4_observability.integrity import verify_event_chain


@dataclass(frozen=True)
class EvidenceBundleArtifact:
    filename: str
    content_type: str
    bytes_data: bytes
    sha256: str


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bundle_signature(manifest_bytes: bytes, events_jsonl: bytes) -> str:
    signed = manifest_bytes + b"\n" + events_jsonl
    return hmac.new(
        settings.audit_signing_secret.encode(),
        signed,
        hashlib.sha256,
    ).hexdigest()


def build_evidence_bundle(*, correlation_id: str, events: list[dict]) -> EvidenceBundleArtifact:
    if not events:
        raise EvidenceBundleNotFoundError(
            f"No telemetry events found for correlation_id '{correlation_id}'"
        )

    first = events[0]
    last = events[-1]
    agent_id = first.get("agent", {}).get("agent_id") or first.get("agent_id") or "unknown-agent"
    decisions = sorted(
        {
            str(event.get("output", {}).get("decision"))
            for event in events
            if event.get("output", {}).get("decision")
        }
    )
    integrity_summary = verify_event_chain(events)

    events_jsonl = "\n".join(json.dumps(event, sort_keys=True) for event in events).encode() + b"\n"
    manifest = {
        "bundle_type": "acr-evidence-bundle",
        "correlation_id": correlation_id,
        "agent_id": agent_id,
        "generated_at": iso_utcnow(),
        "event_count": len(events),
        "event_types": [event.get("event_type") for event in events],
        "decisions": decisions,
        "time_range": {
            "start": first.get("timestamp"),
            "end": last.get("timestamp"),
        },
        "integrity": integrity_summary,
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n"
    checksums = (
        f"{_sha256_bytes(manifest_bytes)}  manifest.json\n"
        f"{_sha256_bytes(events_jsonl)}  events.jsonl\n"
    ).encode()
    bundle_signature = _bundle_signature(manifest_bytes, events_jsonl).encode() + b"\n"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", manifest_bytes)
        archive.writestr("events.jsonl", events_jsonl)
        archive.writestr("checksums.sha256", checksums)
        archive.writestr("bundle.signature", bundle_signature)

    bytes_data = buffer.getvalue()
    return EvidenceBundleArtifact(
        filename=f"{correlation_id}.evidence.zip",
        content_type="application/zip",
        bytes_data=bytes_data,
        sha256=_sha256_bytes(bytes_data),
    )
