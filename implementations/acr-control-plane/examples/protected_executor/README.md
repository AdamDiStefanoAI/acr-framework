# Protected Executor Example

This example shows how to make the ACR gateway a real enforcement point for downstream execution.

The executor exposes a single `/execute` endpoint and refuses to run unless the request includes a valid:
- `X-ACR-Execution-Token`
- `X-ACR-Brokered-Credential`
- request body matching the token's signed payload hash

That means a caller cannot simply replay the executor URL directly with a modified body and bypass the control plane.

## Run

From `implementations/acr-control-plane/`, with the Python environment active:

```bash
# Copy once, then replace both placeholders with distinct random secrets.
cp examples/protected_executor/.env.example examples/protected_executor/.env
# Edit examples/protected_executor/.env before starting either service.
uvicorn examples.protected_executor.app:app --host 127.0.0.1 --port 8010 \
  --env-file examples/protected_executor/.env
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

Configure **both** `EXECUTOR_HMAC_SECRET` and `EXECUTOR_CREDENTIAL_SECRET` with
exactly the same respective values in the gateway and executor processes. Use
two distinct, strong random secrets (at least 32 bytes each). Do not put them in
source control or give them to the agent. The first signs execution authorization;
the second signs brokered downstream credentials. Setting only the first is not
sufficient. The executor's `--env-file` loads its configuration at startup; exports
in another terminal do not update a running process.

In the gateway's environment, set these values before starting/restarting it:

```bash
export EXECUTE_ALLOWED_ACTIONS=true
export EXECUTOR_HMAC_SECRET='<same-value-as-executor-HMAC-secret>'
export EXECUTOR_CREDENTIAL_SECRET='<same-value-as-executor-credential-secret>'
export TOOL_EXECUTOR_MAP_JSON='{
  "query_customer_db":"http://127.0.0.1:8010/execute",
  "send_email":"http://127.0.0.1:8010/execute",
  "create_ticket":"http://127.0.0.1:8010/execute",
  "issue_refund":"http://127.0.0.1:8010/execute"
}'
```

Now the gateway can call the executor. Missing or invalid credentials and payload
tampering return HTTP 401 with `INVALID_EXECUTION_AUTHORIZATION`, without running
the tool. Valid credentials for an unexposed tool return HTTP 403.

## What This Proves

- the control plane can mint short-lived execution authorization
- the control plane can mint short-lived brokered downstream credentials
- the executor can verify that authorization independently
- the executor verifies brokered credential signatures and matches their agent/tool identity to the execution token
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

For a higher-level integration view, see [docs/orchestrators.md](../../docs/orchestrators.md).

## Make It More Reusable

This example now supports a small amount of packaging and runtime configuration:

- [Dockerfile](Dockerfile)
- [env example](.env.example)
- `PROTECTED_EXECUTOR_ALLOWED_TOOLS` to restrict which demo tools are exposed

Example container run:

```bash
docker build -f examples/protected_executor/Dockerfile -t acr-protected-executor .
docker run --rm -p 8010:8010 --env-file examples/protected_executor/.env acr-protected-executor
```

## Important Limitations

This is an application-layer example, not a production-readiness guarantee or an
ACR conformance claim (including Level 2). In particular:

- The brokered credential audience is checked against the caller-supplied
  `X-ACR-Credential-Audience` header, not an executor-configured audience. A validly
  signed credential for another audience can be accepted with its matching header.
- The example returns credential scopes but does not require an execute scope;
  even an empty scope list can pass verification.
- Agent and tool identities are matched between the two credentials, but their
  correlation IDs and approval request IDs are not required to match.
- There is no replay store or idempotency enforcement. Repeating a valid signed
  request before expiration can execute the tool again.

These are existing boundaries of the example; an HTTP 401 for malformed,
missing, or payload-mismatched credentials does not establish those stronger
properties. A production executor must enforce its own expected audience and
required scopes, bind credentials to the same authorization context, and prevent
unwanted duplicate execution. This example alone does not establish complete
enterprise bypass resistance.

For production, pair it with:
- network egress controls
- service identity / mTLS
- secretless or gateway-minted credentials
- IAM scoping so agents cannot talk to protected systems directly
