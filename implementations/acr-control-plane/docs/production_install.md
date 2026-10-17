# ACR Control Plane — Production Install Guide

This is the supported end-to-end production path.

Use the production overlay at [deploy/k8s/overlays/production](../deploy/k8s/overlays/production/README.md), not `deploy/k8s/base`, for real deployments.

## 1. Prerequisites

- Kubernetes cluster
- `ingress-nginx`
- `cert-manager`
- External Secrets Operator
- managed PostgreSQL
- managed Redis
- OIDC identity provider
- S3 or S3-compatible object storage for policy bundles
- internal executor endpoints for refunds, email, tickets, or other governed actions

## 2. Clone and install

```bash
git clone https://github.com/AdamDiStefanoAI/acr-standard.git
cd acr-framework/implementations/acr-control-plane
pip install -e ".[dev]"
```

## 3. Start from the blessed overlay

The production overlay lives at:

- [deploy/k8s/overlays/production/kustomization.yaml](../deploy/k8s/overlays/production/kustomization.yaml)

It assumes:

- OIDC-first operator auth
- `ExternalSecret` as the source of `acr-gateway-secret`
- object-storage-backed policy bundles
- explicit network allowlists for managed services and internal executors

## 4. Configure secrets

Edit [external-secret.yaml](../deploy/k8s/overlays/production/external-secret.yaml) to point at your real secret store.

At minimum, populate:

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `KILLSWITCH_SECRET`
- `SERVICE_OPERATOR_API_KEY`
- `OPERATOR_API_KEYS_JSON`
- `OPERATOR_SESSION_SECRET`
- `OIDC_CLIENT_SECRET`
- `WEBHOOK_HMAC_SECRET`
- `AUDIT_SIGNING_SECRET`
- `EXECUTOR_HMAC_SECRET`
- `EXECUTOR_CREDENTIAL_SECRET`

If you use S3 credentials instead of workload identity, also provide:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## 5. Configure runtime settings

Edit [gateway-configmap-patch.yaml](../deploy/k8s/overlays/production/gateway-configmap-patch.yaml).

Set:

- public hostname and redirect URI
- OIDC issuer and endpoint URLs
- object-storage bucket details
- OTLP endpoint if used

Important production defaults in this path:

- `SCHEMA_BOOTSTRAP_MODE=validate`
- `STRICT_DEPENDENCY_STARTUP=true`
- `REQUIRE_BUNDLE_AUTH=false`

That last setting is intentional: OPA polls bundles directly, so network policy becomes the enforcement boundary for bundle delivery.

## 6. Configure network enforcement

Edit [networkpolicy-production.yaml](../deploy/k8s/overlays/production/networkpolicy-production.yaml).

Replace the placeholder CIDRs for:

- managed PostgreSQL
- managed Redis
- OIDC provider
- object storage
- OTLP collector
- webhook endpoints if used

If your protected executors run in-cluster, place them in a namespace labeled:

```yaml
acr.io/network-zone: protected-executors
```

If they run outside the cluster, add their CIDRs to the gateway egress allowlist instead.

## 7. Pin release images

The overlay ships with release tags as defaults. Before production promotion, replace them with digests:

```bash
kustomize edit set image \
  acr-gateway=ghcr.io/adamdistefanoai/acr-framework/acr-gateway@sha256:<gateway-digest> \
  acr-killswitch=ghcr.io/adamdistefanoai/acr-framework/acr-killswitch@sha256:<killswitch-digest>
```

Then verify those digests using [provenance-and-verification.md](provenance-and-verification.md).

If your registry packages are private, make sure the cluster has image-pull credentials or mirror the images into your internal registry before deployment.

## 8. Build and review the rendered manifests

```bash
kubectl kustomize deploy/k8s/overlays/production
```

Review for:

- no example secrets
- correct hostnames and CIDRs
- expected image references
- expected external secret mappings

## 9. Apply the overlay

```bash
kubectl apply -k deploy/k8s/overlays/production
```

## 10. Confirm policy delivery

The production OPA path uses:

- `/acr/policy-bundles/discovery.json`

Production policy flow:

1. Create or edit a draft in the console.
2. Validate it.
3. Publish a versioned release.
4. Activate the release.
5. OPA pulls the active runtime bundle automatically.

## 11. First operator login

Open:

- `https://your-domain/console`

Use OIDC for normal login. Keep API keys for bootstrap and break-glass only.

## 12. Readiness checklist

- `kubectl -n acr-system get externalsecret,secret`
- `kubectl -n acr-system rollout status deploy/acr-gateway`
- `kubectl -n acr-system rollout status deploy/acr-killswitch`
- `kubectl -n acr-system rollout status deploy/acr-opa`
- OIDC login works
- approval queue works
- kill/restore works
- OPA discovery endpoint is reachable
- active runtime bundle contains the activated release
- executor endpoints succeed
- alerts and dashboards are configured
