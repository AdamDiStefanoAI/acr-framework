# Enterprise Hardening Roadmap

This repo is intended to grow from a strong reference implementation into a deployment pattern that security, platform, and operations teams can trust.

## Priority Order

### 1. Bypass-Resistant Execution
Status: `done`

What landed:
- gateway-issued `X-ACR-Execution-Token`
- payload-bound execution authorization
- protected executor example that rejects direct bypass attempts

Why it matters:
- governance is only real if downstream systems can reject unauthorized direct calls

### 2. Supply-Chain Security Pipeline
Status: `done`

What landed:
- CodeQL workflow
- Semgrep workflow
- Gitleaks workflow
- Trivy filesystem scanning
- CycloneDX SBOM generation

Why it matters:
- the control plane itself has to behave like a security-sensitive product

### 3. Production Secret Management
Status: `done`

What landed:
- production secret generator
- non-dev environment template without copied dev defaults
- CI checks for known dev-secret patterns in production-facing assets

Remaining follow-up:
- add KMS / SealedSecrets / external-secrets reference deployment path

### 4. Gateway-Minted Downstream Credentials
Status: `done`

What landed:
- short-lived brokered downstream credentials minted after allow decisions
- audience and scope-aware credential verification helpers
- protected executor example that validates both execution authorization and brokered credentials

Remaining follow-up:
- tighten IAM and network controls so agents cannot talk to protected systems directly

### 5. Dependency Degradation Semantics
Status: `next`

Scope:
- explicit fail-open / fail-closed matrix by subsystem
- runbooks for Redis, OPA, Postgres, and kill-switch degradation
- load-tested latency and dependency-failure benchmarks

### 6. Governed Baseline Lifecycle
Status: `done`

What landed:
- governed baseline version records with candidate, approved, active, rejected, and superseded states
- operator APIs for propose, approve, activate, reject, and reset flows
- drift scoring that prefers the active governed baseline when one exists
- audit telemetry for baseline governance actions via `human_intervention` events
- operator console support for proposing and reviewing baseline versions

Remaining follow-up:
- baseline diff views and richer operator UX around why one baseline should replace another
- approval queue integration for baseline changes in highly regulated environments

Why it matters:
- a dynamic agent needs an approved path for defining the new normal rather than silent baseline drift

### 7. Orchestrator Adoption Layer
Status: `done`

What landed:
- orchestrator integration guide that positions ACR as the enforcement layer under workflow tools
- `n8n` reference example and starter workflow export
- stronger protected executor packaging and deployment guidance

Remaining follow-up:
- provider-specific adapters beyond `n8n`
- deeper copy-paste examples for LangGraph and similar stacks

Why it matters:
- adoption depends on making ACR infrastructure teams can place underneath existing workflow tools, not optional glue code

### 8. Intent-Aware Telemetry
Status: `done`

What landed:
- optional `intent` payload on gateway evaluation requests
- intent capture in structured telemetry and evidence flows

Remaining follow-up:
- policyable intent validation
- model-based intent drift analysis and alerting

Why it matters:
- behavior alone is often too late; intent metadata gives operators earlier context about why the system is attempting an action

### 9. Provenance and Artifact Signing
Status: `planned`

Scope:
- signed container images
- release provenance / attestation
- verification guidance for deployers

### 10. Kubernetes Policy Validation
Status: `planned`

Scope:
- validate manifests in CI
- add admission-policy examples
- enforce secure defaults for network policy, secrets handling, and runtime settings

### 11. Audit Record Hardening
Status: `planned`

Scope:
- stronger tamper-evidence for telemetry/evidence bundles
- signed evidence manifests
- retention and chain-of-custody guidance

### 12. Operator Incident Workflow
Status: `planned`

Scope:
- responder-first console views
- correlation-centric investigation workflows
- cleaner approval and escalation operations for on-call teams

### 13. Reference Production Deployment
Status: `planned`

Scope:
- one clearly blessed deployment model
- network enforcement story
- identity, secrets, observability, and rollback guidance

## Adoption Test

A team should be able to answer "yes" to all of these before calling the control plane production-ready:

- Can agents only reach sensitive tools through the gateway path?
- Can downstream services verify that the gateway approved the exact payload being executed?
- Are non-dev secrets generated and managed through a real secret-management flow?
- Can we detect code, dependency, container, and secret issues in CI?
- Can we explain system behavior under Redis, OPA, and database failures?
- Can we prove what happened for a single agent action after an incident?
