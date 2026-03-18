# ACR Control Plane — Configuration Reference

All configuration is via environment variables.

- For local development, copy `.env.example` to `.env`
- For production, start from `.env.production.example`
- To generate strong secret values, run `python scripts/generate_secrets.py`

## Required Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://acr:acr_dev_password@localhost:5432/acr_control_plane` | PostgreSQL async connection URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `OPA_URL` | `http://localhost:8181` | Open Policy Agent base URL |
| `KILLSWITCH_URL` | `http://localhost:8443` | Kill switch service base URL |
| `JWT_SECRET_KEY` | `dev_jwt_secret_change_in_production` | **Change in production.** HS256 signing key |
| `KILLSWITCH_SECRET` | `killswitch_dev_secret_change_me` | **Change in production.** Kill switch API secret |

## Optional Variables

| Variable | Default | Description |
|---|---|---|
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_TOKEN_EXPIRE_MINUTES` | `30` | Token TTL in minutes |
| `ACR_ENV` | `development` | Environment tag in telemetry (`development|staging|production`) |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG|INFO|WARNING|ERROR`) |
| `SCHEMA_BOOTSTRAP_MODE` | `auto` | `auto|create|validate|off`. Use `validate` or `off` in production; avoid runtime schema creation. |
| `STRICT_DEPENDENCY_STARTUP` | `false` | If true, fail startup when Redis initialization fails. Recommended in production. |
| `WEBHOOK_URL` | `` | HTTP endpoint to notify on new approval requests |
| `WEBHOOK_HMAC_SECRET` | `` | HMAC-SHA256 signing key for webhook `X-ACR-Signature` header. Required if `WEBHOOK_URL` is set. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `` | OTLP endpoint for traces (e.g. `http://jaeger:4318`) |
| `OTEL_SERVICE_NAME` | `acr-control-plane` | OpenTelemetry service name |
| `OPERATOR_API_KEYS_JSON` | `` | JSON object mapping operator API keys to `{subject, roles}` identities |
| `SERVICE_OPERATOR_API_KEY` | `` | API key the gateway uses for kill-switch service calls |
| `OPERATOR_SESSION_SECRET` | `dev_operator_session_secret_change_me` | Secret used to sign operator browser sessions when OIDC is enabled |
| `OIDC_ENABLED` | `false` | Enable OIDC operator login |
| `OIDC_ISSUER` | `` | Expected OIDC issuer |
| `OIDC_CLIENT_ID` | `` | OIDC client ID |
| `OIDC_CLIENT_SECRET` | `` | OIDC client secret for authorization-code exchange |
| `OIDC_AUTHORIZE_URL` | `` | OIDC authorization endpoint |
| `OIDC_TOKEN_URL` | `` | OIDC token endpoint |
| `OIDC_JWKS_URL` | `` | OIDC JWKS endpoint |
| `OIDC_REDIRECT_URI` | `` | Redirect URI registered with the identity provider |
| `OIDC_SCOPES` | `openid profile email` | Requested OIDC scopes |
| `OIDC_ROLES_CLAIM` | `roles` | Claim used to read external operator roles/groups |
| `OIDC_SUBJECT_CLAIM` | `email` | Claim used for operator identity in ACR |
| `OIDC_ROLE_MAPPING_JSON` | `` | JSON object mapping external IdP roles/groups to ACR roles |
| `OIDC_SESSION_TTL_SECONDS` | `28800` | Operator SSO session TTL in seconds |
| `EXECUTE_ALLOWED_ACTIONS` | `false` | If true, allowed/approved actions are POSTed to the downstream executor route for that tool |
| `TOOL_EXECUTOR_MAP_JSON` | `` | JSON object mapping `tool_name -> executor URL` |
| `EXECUTOR_INTEGRATIONS_JSON` | `` | JSON object defining structured executor adapters for `refund_api`, `email_api`, `ticket_api`, or `http` |
| `EXECUTOR_HMAC_SECRET` | `` | Shared secret used to sign execution payloads and mint short-lived `X-ACR-Execution-Token` headers for downstream verification |
| `EXECUTOR_AUTH_TTL_SECONDS` | `60` | Lifetime of the downstream execution authorization token in seconds |
| `EXECUTOR_CREDENTIAL_SECRET` | `` | Shared secret used to mint short-lived brokered downstream credentials in `X-ACR-Brokered-Credential` |
| `EXECUTOR_CREDENTIAL_TTL_SECONDS` | `300` | Lifetime of the brokered downstream credential in seconds |
| `EXECUTOR_TIMEOUT_SECONDS` | `8.0` | Timeout for downstream executor HTTP calls |
| `POLICY_BUNDLE_BACKEND` | `local` | Bundle publishing backend. Supported values: `local`, `s3`. |
| `POLICY_BUNDLE_LOCAL_DIR` | `./var/policy_bundles` | Filesystem destination for published policy bundles |
| `POLICY_BUNDLE_S3_BUCKET` | `` | S3 bucket or S3-compatible object-store bucket used when `POLICY_BUNDLE_BACKEND=s3` |
| `POLICY_BUNDLE_S3_PREFIX` | `acr/policy-bundles` | Object key prefix used when `POLICY_BUNDLE_BACKEND=s3` |
| `POLICY_BUNDLE_S3_REGION` | `` | Optional AWS region for the S3 client |
| `POLICY_BUNDLE_S3_ENDPOINT_URL` | `` | Optional custom endpoint for S3-compatible storage (MinIO, R2, Ceph, etc.) |
| `POLICY_BUNDLE_PUBLIC_BASE_URL` | `` | Optional public/base URL used for release artifact links |

## Production Checklist

- [ ] Generate a fresh production bundle with `python scripts/generate_secrets.py > .env.production`
- [ ] Generate a 256-bit random `JWT_SECRET_KEY` (`openssl rand -hex 32`)
- [ ] Generate a separate `KILLSWITCH_SECRET`
- [ ] Set `ACR_ENV=production`
- [ ] Set `STRICT_DEPENDENCY_STARTUP=true`
- [ ] Set `SCHEMA_BOOTSTRAP_MODE=validate`
- [ ] Populate `OPERATOR_API_KEYS_JSON` with role-scoped operator identities
- [ ] Configure OIDC and `OPERATOR_SESSION_SECRET` for production operator login
- [ ] Set `SERVICE_OPERATOR_API_KEY` to a key with `killswitch_operator` or `security_admin`
- [ ] Configure `WEBHOOK_URL` for approval notifications
- [ ] Set `OTEL_EXPORTER_OTLP_ENDPOINT` for distributed tracing
- [ ] Set `EXECUTE_ALLOWED_ACTIONS=true` and populate `EXECUTOR_INTEGRATIONS_JSON` or `TOOL_EXECUTOR_MAP_JSON`
- [ ] Set a strong `EXECUTOR_HMAC_SECRET` and require downstream executors to verify `X-ACR-Execution-Token`
- [ ] Set a strong `EXECUTOR_CREDENTIAL_SECRET` and require downstream executors to verify `X-ACR-Brokered-Credential`
- [ ] Set `POLICY_BUNDLE_BACKEND` and a durable bundle destination
- [ ] Use a managed PostgreSQL instance (PgBouncer for connection pooling)
- [ ] Use a managed Redis instance (Redis Sentinel or Cluster for HA)
- [ ] Rotate `JWT_SECRET_KEY` periodically (triggers re-auth for all agents)

Notes:
- `OPERATOR_API_KEYS_JSON` is best treated as a bootstrap mechanism for initial admin access.
- Day-to-day operator key creation, rotation, and revocation can be managed through the control plane and stored in PostgreSQL.
- With `OIDC_ENABLED=true`, operators can sign into the console through the identity provider. API keys remain useful for bootstrap and break-glass operations.
- `.env.production.example` is intentionally placeholder-only so CI can block accidental reuse of local demo secrets in production-facing assets.
- `EXECUTOR_INTEGRATIONS_JSON` supports provider-specific payload mapping for finance refunds, email delivery, ticket creation, and generic internal HTTP services.
- Downstream executors can verify `X-ACR-Execution-Token` against the exact request body to ensure the control plane approved that specific action payload.
- Integrations can define `broker_credentials` with an `audience` and `scopes`, allowing the gateway to mint short-lived downstream credentials per tool invocation.
- For `POLICY_BUNDLE_BACKEND=s3`, install/configure cloud credentials outside the app (for example IAM role, instance profile, IRSA, or standard AWS environment variables).
- Published releases are immutable versioned artifacts. Activating a release also writes a stable per-agent alias at `<agent_id>/active/current.tar.gz`, which is the recommended OPA pull target.
