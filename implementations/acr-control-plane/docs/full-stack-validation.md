# Disposable full-stack validation (proposed; not yet Docker-validated)

This test job builds and starts the actual Compose gateway, migration service,
independent kill switch, PostgreSQL, Redis, OPA, and protected executor. It calls
real HTTP endpoints with an operator key and a gateway-issued agent JWT. It does
not override gateway authentication, policy evaluation, approval persistence,
containment, or executor credential verification.

Only the last enterprise tools are synthetic: a test-only module replaces their
implementations with writes to a JSONL ledger inside the executor container.
The ledger survives that container's stop/start cycle. The added observer endpoint
has no authentication and must never be deployed; its test port is bound only to
127.0.0.1 on a disposable runner. No real customer records, payments, email, model
services, production secrets, or shared databases are used.

## Proposed checks

- Register an agent with real operator auth and issue its JWT; reject unauthenticated registration.
- ALLOW executes the authorized tool and exact parameters once.
- DENY produces no tool execution.
- MODIFY executes the transformed parameters once, with original synthetic PII absent.
- ESCALATE remains pending without execution; approve executes the approved tool/payload once;
  reject executes nothing; repeating the approval is rejected without another execution.
- Reject a direct unsigned executor request and a payload changed after signing.
- Stop/restart executor, OPA, Redis, and Postgres separately; verify no new tool effect
  during failure and successful execution after restoration.
- Kill an agent, verify blocked execution, stop the kill-service process, verify
  the existing killed state remains enforced through Redis, then restore service
  and explicitly restore the agent.
- Retrieve a persisted correlated allow event and its evidence archive; verify
  correlation, agent, decision, archive SHA-256, and internal file checksums.

This is bounded acceptance testing, not a production-safety or conformance claim.
It does not test gateway outage, concurrent or replayed executor authority,
30-second kill-switch SLA, all graduated containment tiers, high-risk durable-log
failure gating, recovery after VM loss, or actual enterprise side effects.
Approval endpoint replay rejection is distinct from executor replay prevention.
The content checks do not constitute independent cryptographic audit-signature
verification.

## Isolation and limits

The job has repository permission `contents: read`; it does write synthetic test
records inside disposable services. It does not write repository content, publish
images, deploy, or use GitHub secrets. Credentials in the workflow are deliberately
public, disposable fixture values and must never be reused elsewhere.

The standard Ubuntu GitHub-hosted runner gets a unique Compose project per run.
Database/Redis/OPA/kill-service ports are not published; gateway and fixture ports
bind only to runner loopback. Compose >=2.24.4 is required for override/reset tags.
No privileged container, Docker socket mount into a test container, host directory
mount, or system-security configuration change is added. Existing deployment
resource caps remain in force and the executor is capped at 0.5 CPU and 256 MiB.
The workflow has a 30-minute job limit, 5-minute image pull, 12-minute build/start,
8-minute checks, and 3-minute cleanup limits. Cleanup runs under `always()` and
removes only the unique project's containers/volumes; GitHub disposes the runner
if forced job termination prevents that step. Evidence retention is one day.

Service logs contain synthetic data, not guaranteed redacted output. Test code
never prints/stores its issued JWT, and logs must remain limited to synthetic data.

## Deployment configuration fixes included

The base Compose gateway now forwards both `EXECUTOR_CREDENTIAL_SECRET` and
`KILLSWITCH_SECRET`. Previously the brokered credential secret was absent and a
custom kill-switch secret reached only the kill-service process. Source-level
regressions check that both authorization secrets reach the gateway and that both
services receive the same kill-switch setting. Passing these regressions is not
proof that Docker startup succeeds.

## Execution and evidence

The workflow runs on a draft PR affecting the implementation, and supports
workflow_dispatch once GitHub recognizes it on the default branch. Publishing
this workflow or creating its PR requires owner approval. No run has occurred
in the current cloud workspace because it has no usable container runtime.

`full-stack-evidence/` records revision, Docker versions, observations, exact tool
payloads, first failure (preserved even if recovery also fails), container status,
service logs, event chain, and an evidence archive. Passing unit/static checks for
this proposed code must not be presented as a full-stack PASS. The first real run
may expose startup/configuration defects; retain failures rather than weakening
assertions to obtain green results.
