# Protected Executor Example

This example shows how to make the ACR gateway a real enforcement point for downstream execution.

The executor exposes a single `/execute` endpoint and refuses to run unless the request includes a valid:
- `X-ACR-Execution-Token`
- request body matching the token's signed payload hash

That means a caller cannot simply replay the executor URL directly with a modified body and bypass the control plane.

## Run

From the project root:

```bash
uvicorn examples.protected_executor.app:app --host 127.0.0.1 --port 8010
```

Health check:

```bash
curl http://127.0.0.1:8010/health
```

## Connect It To The Gateway

Set the gateway to execute allowed actions and point tools at the protected executor:

```bash
export EXECUTE_ALLOWED_ACTIONS=true
export EXECUTOR_HMAC_SECRET=replace-with-a-strong-random-secret
export TOOL_EXECUTOR_MAP_JSON='{
  "query_customer_db":"http://127.0.0.1:8010/execute",
  "send_email":"http://127.0.0.1:8010/execute",
  "create_ticket":"http://127.0.0.1:8010/execute",
  "issue_refund":"http://127.0.0.1:8010/execute"
}'
```

Now the gateway can call the executor, but direct callers without a valid execution token should be rejected.

## What This Proves

- the control plane can mint short-lived execution authorization
- the executor can verify that authorization independently
- the exact request body is bound to the authorization token
- bypass attempts that alter the payload can be rejected before tool execution

## Important Limitation

This is an application-layer enforcement pattern, not a complete enterprise bypass-resistance story by itself.

For production, pair it with:
- network egress controls
- service identity / mTLS
- secretless or gateway-minted credentials
- IAM scoping so agents cannot talk to protected systems directly
