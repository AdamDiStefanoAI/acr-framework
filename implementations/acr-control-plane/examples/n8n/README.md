# n8n Integration Example

This example shows how to use `n8n` as the workflow layer while keeping the ACR control plane as the enforcement layer for sensitive actions.

## The Core Idea

`n8n` should decide *what it wants to do next*.

ACR should decide *whether that action is allowed to happen at all*.

For sensitive steps, do not wire `n8n` directly to internal ticketing, refund, email, or infrastructure systems. Wire it to `POST /acr/evaluate` instead.

## Reference Flow

```text
n8n Trigger / Workflow
  -> Build action payload
  -> HTTP Request: POST /acr/evaluate
  -> Switch on decision
     -> allow: continue with gateway-managed execution result
     -> deny: stop and surface the reason
     -> escalate: notify operators / wait for approval
```

## Files In This Example

- [workflow JSON](/Users/adamdistefano/Desktop/control_plane/examples/n8n/acr_sensitive_action_workflow.json)
- [protected executor example](/Users/adamdistefano/Desktop/control_plane/examples/protected_executor/README.md)

The workflow JSON is meant as a starting point, not a complete production export.

## Assumptions

This example assumes:

- ACR runs at `http://localhost:8000`
- the protected executor runs at `http://127.0.0.1:8010`
- you have already registered an agent and issued a JWT
- the gateway is configured with `EXECUTE_ALLOWED_ACTIONS=true`

## Example Action Payload

The HTTP Request node should send something like:

```json
{
  "agent_id": "customer-support-01",
  "action": {
    "tool_name": "create_ticket",
    "parameters": {
      "title": "Customer issue follow-up",
      "body": "Customer requested a call back",
      "priority": "normal"
    },
    "description": "Create support ticket from workflow"
  },
  "context": {
    "session_id": "n8n-run-123",
    "hourly_spend_usd": 0.25
  }
}
```

And it should include:

```text
Authorization: Bearer <agent JWT>
Content-Type: application/json
```

## How To Handle The Response In n8n

When the ACR response comes back:

- `decision=allow`
  Use the returned `execution_result` if gateway-managed execution is enabled.
- `decision=deny`
  Stop the workflow and store the reason in workflow logs or a task comment.
- `decision=escalate`
  Notify an operator and persist the `approval_request_id`.

## Why This Pattern Matters

If `n8n` talks directly to internal systems, ACR is only advisory.

If `n8n` must go through ACR and the downstream executor rejects non-ACR traffic, ACR becomes the real control boundary.

That is the recommended production posture.

## Production Notes

- Keep the protected executor on an internal network.
- Do not expose direct credentials for protected systems to the workflow builder.
- Prefer short-lived brokered credentials minted by the gateway.
- Treat `n8n` as the orchestration UX, not the final enforcement point.
