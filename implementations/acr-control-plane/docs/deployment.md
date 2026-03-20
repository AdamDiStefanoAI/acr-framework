# ACR Control Plane — Deployment Guide

## Local Development

```bash
# Start full stack
docker-compose up --build

# Run tests (no external services required)
pip install -e ".[dev]"
pytest tests/ -v

# Watch logs
docker-compose logs -f acr-gateway
```

## Production Deployment

### Security hardening

1. **Rotate all secrets** before deploying:
   ```bash
   JWT_SECRET_KEY=$(openssl rand -hex 32)
   KILLSWITCH_SECRET=$(openssl rand -hex 32)
   ```

2. **Network isolation:** The kill switch service (port 8443) should only be reachable from:
   - The ACR gateway (for read-only status checks)
   - Operations tooling (for write operations)
   - NOT exposed to the public internet

3. **TLS:** Put both services behind a TLS-terminating reverse proxy (nginx, Caddy, or cloud load balancer).

4. **PostgreSQL:** Use a managed RDS/Cloud SQL instance. Enable SSL connections in `DATABASE_URL`.

5. **Redis:** Use a managed ElastiCache/Redis Cloud instance with AUTH enabled.

6. **Operator auth:** Prefer OIDC SSO for operators. Keep API keys as bootstrap and break-glass only.

### Resource requirements

| Service | Min vCPU | Min Memory | Notes |
|---|---|---|---|
| `acr-gateway` | 0.5 | 512 MB | Scale horizontally for higher throughput |
| `acr-killswitch` | 0.25 | 256 MB | Single instance is sufficient; stateless except Redis |
| `opa` | 0.5 | 512 MB | Bundle server mode recommended for large policy sets |
| PostgreSQL | 1 | 2 GB | Managed instance recommended |
| Redis | 0.5 | 512 MB | Used for kill switch state and rate limit counters |

### Environment variables (production)

See [configuration.md](configuration.md).

### Health checks

- Gateway: `GET http://acr-gateway:8000/acr/health`
- Gateway liveness: `GET http://acr-gateway:8000/acr/live`
- Gateway readiness: `GET http://acr-gateway:8000/acr/ready`
- Kill switch: `GET http://acr-killswitch:8443/health`
- Kill switch readiness: `GET http://acr-killswitch:8443/ready`
- OPA: `GET http://opa:8181/health`

### Alembic migrations

Run migrations before starting the gateway:

```bash
PYTHONPATH=src alembic upgrade head
```

Or in Docker:

```bash
docker run --env-file .env acr-gateway sh -c "PYTHONPATH=/app/src alembic upgrade head"
```

### OPA runtime bundle mode

For production, prefer OPA bundle/discovery mode over mounting the local `./policies` directory.
Point OPA at the control plane’s discovery document so activated GUI releases become the live policy set.

Example OPA startup:

```bash
opa run \
  --server \
  --addr=0.0.0.0:8181 \
  --log-format=json \
  --set=services.acr.url=http://acr-gateway:8000 \
  --set=bundles.acr_active_runtime.service=acr \
  --set=bundles.acr_active_runtime.resource=/acr/policy-bundles/active.tar.gz
```

Or use the discovery document directly:

```bash
opa run \
  --server \
  --addr=0.0.0.0:8181 \
  --log-format=json \
  --set=services.acr.url=http://acr-gateway:8000 \
  --set=discovery.resource=/acr/policy-bundles/discovery.json
```

This mode gives you:
- immutable published releases
- explicit operator activation
- one aggregate active bundle for all live agents
- no manual per-agent OPA wiring

### Production guardrails

1. Set `SCHEMA_BOOTSTRAP_MODE=validate` and run Alembic externally before deployment.
2. Set `STRICT_DEPENDENCY_STARTUP=true` so the service refuses to start without Redis.
3. Require operator API keys on sensitive endpoints via `OPERATOR_API_KEYS_JSON`.
4. Use `EXECUTE_ALLOWED_ACTIONS=true` only after each `tool_name` is mapped in `TOOL_EXECUTOR_MAP_JSON` or `EXECUTOR_INTEGRATIONS_JSON`.
5. Route all executor URLs to internal, purpose-built services. Do not point them at arbitrary third-party endpoints directly.
6. Prefer `EXECUTOR_INTEGRATIONS_JSON` for refunds, email, and ticketing so payloads are shaped consistently for internal systems.

### Orchestrator deployment model

If you are layering ACR under `n8n`, LangGraph, or a custom workflow tool:

1. Treat the workflow tool as the experience layer, not the final enforcement layer.
2. Route sensitive workflow steps to `POST /acr/evaluate`.
3. Keep protected executors and business APIs on internal networks.
4. Do not give the workflow tool standing direct credentials for protected systems when ACR is meant to govern them.
5. Require downstream services to verify `X-ACR-Execution-Token` and `X-ACR-Brokered-Credential`.

Reference guide:

- [orchestrator integration guide](/Users/adamdistefano/Desktop/control_plane/docs/orchestrators.md)
- [n8n example](/Users/adamdistefano/Desktop/control_plane/examples/n8n/README.md)

### Scaling

The gateway is stateless — scale horizontally behind a load balancer. All state lives in PostgreSQL and Redis.

The kill switch service is stateless — Redis holds all state. Multiple instances can run behind a load balancer.

### Monitoring

Key metrics to alert on:
- `acr_gateway_p95_latency_ms > 200` — SLA violation
- `policy_deny_rate > 0.2` — unusually high denial rate
- `drift_score > 0.6` — agent entering containment tier
- `approval_queue_depth > 50` — approval backlog
- `kill_switch_activations` — any activation should page on-call

### Backup

- PostgreSQL: standard pg_dump / managed instance backups
- Redis: not critical (kill switch state can be rebuilt; contains only `is_killed` flags)
- OPA policies: policies are in Git; no backup needed

### Kubernetes manifests

This repo includes a production-oriented Kubernetes base at
[kustomization.yaml](/Users/adamdistefano/Desktop/control_plane/deploy/k8s/base/kustomization.yaml).

It includes:
- gateway deployment/service
- kill-switch deployment/service
- OPA deployment/service in discovery mode
- config and secret templates
- starter network policy

Apply with:

```bash
kubectl apply -k deploy/k8s/base
```
