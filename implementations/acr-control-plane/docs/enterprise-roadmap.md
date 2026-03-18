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

### 6. Provenance and Artifact Signing
Status: `planned`

Scope:
- signed container images
- release provenance / attestation
- verification guidance for deployers

### 7. Kubernetes Policy Validation
Status: `planned`

Scope:
- validate manifests in CI
- add admission-policy examples
- enforce secure defaults for network policy, secrets handling, and runtime settings

### 8. Audit Record Hardening
Status: `planned`

Scope:
- stronger tamper-evidence for telemetry/evidence bundles
- signed evidence manifests
- retention and chain-of-custody guidance

### 9. Operator Incident Workflow
Status: `planned`

Scope:
- responder-first console views
- correlation-centric investigation workflows
- cleaner approval and escalation operations for on-call teams

### 10. Reference Production Deployment
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
