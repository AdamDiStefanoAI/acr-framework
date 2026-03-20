# Protected Executor Example

This example shows how to make the ACR gateway a real enforcement point for downstream execution.

The executor exposes a single `/execute` endpoint and refuses to run unless the request includes a valid:
- `X-ACR-Execution-Token`
- `X-ACR-Brokered-Credential`
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

Metadata:

```bash
curl http://127.0.0.1:8010/metadata
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
- the control plane can mint short-lived brokered downstream credentials
- the executor can verify that authorization independently
- the executor can enforce audience/scope-aware credentials instead of trusting the caller directly
- the exact request body is bound to the authorization token
- bypass attempts that alter the payload can be rejected before tool execution

## Why This Matters For Orchestrators

This pattern is what turns ACR into infrastructure instead of advice.

If an orchestrator like `n8n` or LangGraph can still call your refund, email, or ticket APIs directly, then ACR is optional. If those systems only accept requests that carry valid gateway authorization, then the orchestrator is forced to go through the control plane.

That is the recommended production model:

- workflow tool decides what action it wants to attempt
- ACR evaluates the action
- protected executor verifies that ACR explicitly authorized the exact payload
- internal system executes only after both checks pass

For a higher-level integration view, see [docs/orchestrators.md](/Users/adamdistefano/Desktop/control_plane/docs/orchestrators.md).

## Make It More Reusable

This example now supports a small amount of packaging and runtime configuration:

- [Dockerfile](/Users/adamdistefano/Desktop/control_plane/examples/protected_executor/Dockerfile)
- [env example](/Users/adamdistefano/Desktop/control_plane/examples/protected_executor/.env.example)
- `PROTECTED_EXECUTOR_ALLOWED_TOOLS` to restrict which demo tools are exposed

Example container run:

```bash
docker build -f examples/protected_executor/Dockerfile -t acr-protected-executor .
docker run --rm -p 8010:8010 --env-file examples/protected_executor/.env.example acr-protected-executor
```

## Important Limitation

This is an application-layer enforcement pattern, not a complete enterprise bypass-resistance story by itself.

For production, pair it with:
- network egress controls
- service identity / mTLS
- secretless or gateway-minted credentials
- IAM scoping so agents cannot talk to protected systems directly
