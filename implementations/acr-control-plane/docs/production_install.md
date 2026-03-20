# ACR Control Plane — Production Install Guide

This is the shortest end-to-end path for taking the repo from GitHub to a real production deployment.

## 1. Prerequisites

- Kubernetes cluster with ingress/load balancing
- Managed PostgreSQL
- Managed Redis
- OIDC identity provider
- Internal business APIs for refunds, outbound email, and ticket creation
- Object storage for policy bundles if using `POLICY_BUNDLE_BACKEND=s3`

## 2. Clone and install

```bash
git clone https://github.com/SynergeiaLabs/acr-framework.git
cd acr-framework/implementations/acr-control-plane
pip install -e ".[dev]"
```

## 3. Configure secrets

Start with [gateway-secret.example.yaml](/Users/adamdistefano/Desktop/control_plane/deploy/k8s/base/gateway-secret.example.yaml) and replace every placeholder.

Generate strong values for:
- `JWT_SECRET_KEY`
- `KILLSWITCH_SECRET`
- `OPERATOR_SESSION_SECRET`
- `WEBHOOK_HMAC_SECRET`
- `EXECUTOR_HMAC_SECRET`

## 4. Configure OIDC operator login

Set these in [gateway-configmap.yaml](/Users/adamdistefano/Desktop/control_plane/deploy/k8s/base/gateway-configmap.yaml):

- `OIDC_ENABLED=true`
- `OIDC_ISSUER`
- `OIDC_CLIENT_ID`
- `OIDC_CLIENT_SECRET`
- `OIDC_AUTHORIZE_URL`
- `OIDC_TOKEN_URL`
- `OIDC_JWKS_URL`
- `OIDC_REDIRECT_URI`
- `OIDC_ROLE_MAPPING_JSON`

Recommended role mapping:
- platform admins -> `agent_admin`, `security_admin`, `auditor`, `approver`, `killswitch_operator`
- approvers -> `approver`
- auditors -> `auditor`

## 5. Configure executor integrations

Set `EXECUTE_ALLOWED_ACTIONS=true` and define `EXECUTOR_INTEGRATIONS_JSON`.

Supported providers:
- `refund_api`
- `email_api`
- `ticket_api`
- `http`

Example:

```json
{
  "issue_refund": {
    "provider": "refund_api",
    "url": "https://refunds.internal/api/refunds",
    "api_key": "env:FINANCE_EXECUTOR_API_KEY",
    "default_currency": "USD"
  },
  "send_email": {
    "provider": "email_api",
    "url": "https://messaging.internal/api/send",
    "api_key": "env:EMAIL_EXECUTOR_API_KEY",
    "from_address": "ops@example.com"
  },
  "create_ticket": {
    "provider": "ticket_api",
    "url": "https://tickets.internal/api/tickets",
    "api_key": "env:TICKET_EXECUTOR_API_KEY",
    "default_queue": "operations"
  }
}
```

## 6. Configure policy bundle delivery

If using object storage, set:
- `POLICY_BUNDLE_BACKEND=s3`
- `POLICY_BUNDLE_S3_BUCKET`
- `POLICY_BUNDLE_S3_PREFIX`

## 7. Run migrations

```bash
PYTHONPATH=src alembic upgrade head
```

## 8. Deploy Kubernetes base

```bash
kubectl apply -k deploy/k8s/base
```

## 9. Confirm runtime policy wiring

The provided OPA deployment uses:
- `/acr/policy-bundles/discovery.json`

Production policy flow:
1. Create or edit a draft in the GUI
2. Validate it
3. Publish a versioned release
4. Activate the release
5. OPA pulls the active runtime bundle automatically

## 10. First operator login

Open:
- `https://your-domain/console`

Use OIDC for normal login. Keep API keys for bootstrap and break-glass only.

## 11. First production agent

From the console:
- register the agent
- issue an agent token
- create or load a policy draft
- publish and activate the policy
- verify the agent can call `/acr/evaluate`

## 12. Readiness checklist

- OIDC login works
- approval queue works
- kill/restore works
- OPA discovery endpoint is reachable
- active runtime bundle contains the activated release
- refund/email/ticket executor endpoints succeed
- alerts and dashboards are configured
