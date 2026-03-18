from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyBundleArtifact:
    filename: str
    content_type: str
    bytes_data: bytes
    sha256: str


def build_policy_bundle(
    *,
    release_id: str,
    agent_id: str,
    version: int,
    manifest: dict,
    rego_policy: str,
) -> PolicyBundleArtifact:
    bundle_name = f"{agent_id}-v{version}.tar.gz"
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gz_buffer:
        with tarfile.open(fileobj=gz_buffer, mode="w") as tar:
            files = {
                "bundle/manifest.json": json.dumps(manifest, indent=2).encode(),
                "bundle/policy.rego": rego_policy.encode(),
                "bundle/metadata.json": json.dumps(
                    {
                    "release_id": release_id,
                    "agent_id": agent_id,
                    "version": version,
                },
                indent=2,
            ).encode(),
        }
            for name, payload in files.items():
                info = tarfile.TarInfo(name=name)
                info.size = len(payload)
                info.mtime = 0
                tar.addfile(info, io.BytesIO(payload))
    bytes_data = buffer.getvalue()
    return PolicyBundleArtifact(
        filename=bundle_name,
        content_type="application/gzip",
        bytes_data=bytes_data,
        sha256=hashlib.sha256(bytes_data).hexdigest(),
    )
