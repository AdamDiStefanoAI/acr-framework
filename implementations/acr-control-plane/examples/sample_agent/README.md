# ACR Sample Agent

A simple demonstration agent that exercises all six ACR control pillars.

## Prerequisites

1. Start the full ACR stack:
   ```bash
   cd ../..   # project root
   docker-compose up --build
   ```

2. Install the HTTP client:
   ```bash
   pip install httpx
   ```

3. Export the development operator API key used for agent onboarding:
   ```bash
   export ACR_OPERATOR_API_KEY=dev-operator-key
   ```

## Run

```bash
python examples/sample_agent/agent.py
```

## What it demonstrates

| Step | Action | Expected result |
|---|---|---|
| 1 | Register agent | 201 Created |
| 2a | `query_customer_db` | ✓ allow |
| 2b | `send_email` | ✓ allow |
| 2c | `create_ticket` | ✓ allow |
| 3 | `delete_customer` | ✗ deny (Pillar 2: forbidden tool) |
| 4 | `issue_refund $250` | ⏳ escalate (Pillar 6: approval required) |

After running, check:
- Telemetry: `GET http://localhost:8000/acr/events?agent_id=customer-support-01`
- Approval queue: `GET http://localhost:8000/acr/approvals`
- Drift score: `GET http://localhost:8000/acr/drift/customer-support-01`

## Pair It With A Protected Executor

If you want to demo bypass-resistant downstream execution instead of gateway-only decisioning, also run the [protected executor example](../protected_executor/README.md).

That executor verifies the gateway-issued `X-ACR-Execution-Token` before running a tool, which makes the "only the control plane can authorize execution" pattern explicit.
