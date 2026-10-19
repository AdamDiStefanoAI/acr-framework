# ACR Sample Agent

A simple demonstration agent that exercises all six ACR control pillars.

## Prerequisites

Use a Git checkout of this repository, Python 3.11 or 3.12, and Docker Compose v2. All commands below start at the **repository root** unless noted. Use an isolated local environment; the example credentials are not suitable for production.

### Terminal 1: start the local stack

```bash
cd implementations/acr-control-plane
cp .env.example .env
export OPERATOR_API_KEYS_JSON='{"dev-operator-key":{"subject":"dev-operator","roles":["agent_admin","approver","security_admin","auditor","killswitch_operator"]}}'
export SERVICE_OPERATOR_API_KEY=dev-operator-key
docker compose up --build
```

The operator keys must be configured before the containers start. `.env.example` leaves them blank; exporting `ACR_OPERATOR_API_KEY` for the client alone does not configure the server. The stack runs database migrations automatically. Keep this terminal running and wait until `curl http://localhost:8000/acr/health` succeeds before starting the sample.

### Terminal 2: install and run the sample

From the repository root in a second terminal:

```bash
cd implementations/acr-control-plane
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
export ACR_OPERATOR_API_KEY=dev-operator-key
python examples/sample_agent/agent.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` and use `$env:ACR_OPERATOR_API_KEY = "dev-operator-key"`. Set the server environment variables in Terminal 1 using PowerShell's `$env:NAME = 'value'` syntax as well.

Install the control-plane package, not only `httpx`: the sample imports `ACRClient` and the request models from the local `acr` package. It evaluates example actions against your local gateway; it does not connect to a real customer database, email provider, or payment service.

For code changes and tests, use the [contribution guide](../../../../CONTRIBUTING.md#code-contributions).

The sample now uses the official Python SDK:

- `ACRClient.ensure_agent_registered(...)`
- `ACRClient.issue_agent_session(...)`
- `ACRAgentSession.evaluate_action(...)`

## What it demonstrates

| Step | Action | Expected result |
|---|---|---|
| 1 | Register agent | 201 Created |
| 2a | `query_customer_db` | ✓ allow |
| 2b | `send_email` | ~ modify (email address redacted by output controls) |
| 2c | `create_ticket` | ✓ allow |
| 3 | `delete_customer` | ✗ deny (Pillar 2: forbidden tool) |
| 4 | `issue_refund $250` | ⏳ escalate (Pillar 6: approval required) |

The default sample email includes a synthetic email address, so output controls return `modify`. This is a decision demonstration: the ordinary configuration has `EXECUTE_ALLOWED_ACTIONS=false`, and does not send email or execute real downstream tools.

After running, check:
- Telemetry: `GET http://localhost:8000/acr/events?agent_id=customer-support-01`
- Approval queue: `GET http://localhost:8000/acr/approvals`
- Drift score: `GET http://localhost:8000/acr/drift/customer-support-01`

## Pair It With A Protected Executor

If you want to demo bypass-resistant downstream execution instead of gateway-only decisioning, also run the [protected executor example](../protected_executor/README.md).

That executor verifies the gateway-issued `X-ACR-Execution-Token` before running a tool, which makes the "only the control plane can authorize execution" pattern explicit.
