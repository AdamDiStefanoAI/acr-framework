from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from acr.common.errors import PolicyValidationError
from acr.config import policy_bundle_local_path, settings
from acr.policy_studio.bundles import PolicyBundleArtifact


@dataclass(frozen=True)
class PublishedBundle:
    backend: str
    uri: str
    sha256: str


def _public_bundle_uri(*, agent_id: str, version: int, filename: str) -> str | None:
    if settings.policy_bundle_public_base_url:
        return f"{settings.policy_bundle_public_base_url.rstrip('/')}/{agent_id}/v{version}/{filename}"
    return None


def _public_active_bundle_uri(*, agent_id: str) -> str | None:
    if settings.policy_bundle_public_base_url:
        return f"{settings.policy_bundle_public_base_url.rstrip('/')}/{agent_id}/active/current.tar.gz"
    return None


def _publish_local_bundle(
    *,
    agent_id: str,
    version: int,
    artifact: PolicyBundleArtifact,
) -> PublishedBundle:
    root = policy_bundle_local_path()
    target_dir = root / agent_id / f"v{version}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / artifact.filename
    target.write_bytes(artifact.bytes_data)

    uri = _public_bundle_uri(agent_id=agent_id, version=version, filename=artifact.filename)
    if uri is None:
        uri = str(target.resolve())

    return PublishedBundle(
        backend="local",
        uri=uri,
        sha256=artifact.sha256,
    )


def _publish_local_active_bundle(
    *,
    agent_id: str,
    artifact: PolicyBundleArtifact,
) -> PublishedBundle:
    root = policy_bundle_local_path()
    target_dir = root / agent_id / "active"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "current.tar.gz"
    target.write_bytes(artifact.bytes_data)

    uri = _public_active_bundle_uri(agent_id=agent_id)
    if uri is None:
        uri = str(target.resolve())

    return PublishedBundle(
        backend="local",
        uri=uri,
        sha256=artifact.sha256,
    )


def _s3_client():
    try:
        import boto3
    except ModuleNotFoundError as exc:
        raise PolicyValidationError(
            "boto3 is required for POLICY_BUNDLE_BACKEND=s3"
        ) from exc

    client_kwargs: dict[str, str] = {}
    if settings.policy_bundle_s3_region:
        client_kwargs["region_name"] = settings.policy_bundle_s3_region
    if settings.policy_bundle_s3_endpoint_url:
        client_kwargs["endpoint_url"] = settings.policy_bundle_s3_endpoint_url
    return boto3.client("s3", **client_kwargs)


def _publish_s3_bundle(
    *,
    agent_id: str,
    version: int,
    artifact: PolicyBundleArtifact,
) -> PublishedBundle:
    bucket = settings.policy_bundle_s3_bucket.strip()
    if not bucket:
        raise PolicyValidationError(
            "POLICY_BUNDLE_S3_BUCKET must be set for POLICY_BUNDLE_BACKEND=s3"
        )

    prefix = settings.policy_bundle_s3_prefix.strip().strip("/")
    key = "/".join(
        part for part in [prefix, agent_id, f"v{version}", artifact.filename] if part
    )

    client = _s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=artifact.bytes_data,
        ContentType=artifact.content_type,
        Metadata={"sha256": artifact.sha256},
    )

    uri = _public_bundle_uri(agent_id=agent_id, version=version, filename=artifact.filename)
    if uri is None:
        uri = f"s3://{bucket}/{key}"

    return PublishedBundle(
        backend="s3",
        uri=uri,
        sha256=artifact.sha256,
    )


def _publish_s3_active_bundle(
    *,
    agent_id: str,
    artifact: PolicyBundleArtifact,
) -> PublishedBundle:
    bucket = settings.policy_bundle_s3_bucket.strip()
    if not bucket:
        raise PolicyValidationError(
            "POLICY_BUNDLE_S3_BUCKET must be set for POLICY_BUNDLE_BACKEND=s3"
        )

    prefix = settings.policy_bundle_s3_prefix.strip().strip("/")
    key = "/".join(part for part in [prefix, agent_id, "active", "current.tar.gz"] if part)

    client = _s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=artifact.bytes_data,
        ContentType=artifact.content_type,
        Metadata={"sha256": artifact.sha256},
    )

    uri = _public_active_bundle_uri(agent_id=agent_id)
    if uri is None:
        uri = f"s3://{bucket}/{key}"

    return PublishedBundle(
        backend="s3",
        uri=uri,
        sha256=artifact.sha256,
    )


def publish_policy_bundle(
    *,
    agent_id: str,
    version: int,
    artifact: PolicyBundleArtifact,
) -> PublishedBundle:
    backend = settings.policy_bundle_backend
    if backend == "local":
        return _publish_local_bundle(agent_id=agent_id, version=version, artifact=artifact)
    if backend == "s3":
        return _publish_s3_bundle(agent_id=agent_id, version=version, artifact=artifact)
    raise PolicyValidationError(
        f"Unsupported POLICY_BUNDLE_BACKEND '{backend}'. "
        "Supported backends: local, s3."
    )


def publish_active_policy_bundle(
    *,
    agent_id: str,
    artifact: PolicyBundleArtifact,
) -> PublishedBundle:
    backend = settings.policy_bundle_backend
    if backend == "local":
        return _publish_local_active_bundle(agent_id=agent_id, artifact=artifact)
    if backend == "s3":
        return _publish_s3_active_bundle(agent_id=agent_id, artifact=artifact)
    raise PolicyValidationError(
        f"Unsupported POLICY_BUNDLE_BACKEND '{backend}'. "
        "Supported backends: local, s3."
    )
