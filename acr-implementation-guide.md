# ACR Framework™ — Implementation Guide

**Version:** 1.0  
**Status:** Draft  
**Last Updated:** March 2026

> This guide provides reference architectures, deployment patterns, and integration guidance for implementing the ACR runtime control plane in production environments.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture Decision Framework](#architecture-decision-framework)
4. [Reference Architecture: Kubernetes + OPA](#reference-architecture-kubernetes--opa)
5. [Reference Architecture: AWS Serverless + Cedar](#reference-architecture-aws-serverless--cedar)
6. [Reference Architecture: API Gateway + Custom](#reference-architecture-api-gateway--custom)
7. [Pillar-by-Pillar Implementation](#pillar-by-pillar-implementation)
8. [Telemetry & Observability Setup](#telemetry--observability-setup)
9. [Policy Authoring Guide](#policy-authoring-guide)
10. [Testing & Validation](#testing--validation)
11. [Migration Path](#migration-path)
12. [Operational Runbook](#operational-runbook)

---

## Overview

The ACR control plane sits between autonomous AI systems and enterprise resources. It intercepts agent actions at runtime and applies identity verification, policy enforcement, drift detection, observability, containment, and human authority controls before those actions reach downstream systems.

This guide covers three reference deployment patterns, with step-by-step integration guidance for each of the six ACR pillars.

### What You're Building

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent Runtime                       │
│  (LangGraph, CrewAI, AutoGen, custom orchestrator, etc.) │
└──────────────────────┬──────────────────────────────────┘
                       │  action request
                       ▼
┌─────────────────────────────────────────────────────────┐
│               ACR CONTROL PLANE                          │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Identity │ │  Policy  │ │  Drift   │ │Observabil.│  │
│  │ Binding  │ │ Enforce. │ │ Detect.  │ │  Logging  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│  ┌──────────────────┐ ┌────────────────────────────┐    │
│  │   Containment    │ │     Human Authority        │    │
│  └──────────────────┘ └────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │  approved action
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Enterprise Resources                        │
│  (APIs, databases, tools, external services, workflows)  │
└─────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Fail-secure by default.** If the control plane is unreachable, agent actions are blocked — not allowed.
2. **Latency budget: <200ms total.** The control plane must not make agents unusable. Target 50ms for identity, 100ms for policy, 20ms per action authorization.
3. **Policy-as-code.** All enforcement rules are versioned, testable, and deployable through CI/CD — not configured through UI clicks.
4. **Agent-agnostic.** The control plane works with any agent framework. It intercepts actions, not prompts.
5. **Observable by default.** Every control plane decision is logged with correlation IDs for end-to-end trace reconstruction.

---

## Prerequisites

Before implementing ACR, ensure your organization has:

| Prerequisite | Why It Matters | Minimum Viable |
|---|---|---|
| **Agent inventory** | You cannot control what you haven't catalogued | Spreadsheet of all deployed AI agents with owners, purposes, and tools |
| **Identity infrastructure** | Agents need machine identities | Any IAM system — cloud IAM, Vault, SPIFFE, or even API keys with rotation |
| **Policy ownership** | Someone must define what agents can and cannot do | Designated owner per agent (engineering lead or product owner) |
| **Logging infrastructure** | Observability requires a destination | Any structured log pipeline — ELK, Datadog, CloudWatch, or even structured files |
| **Incident response process** | Containment requires a playbook | Basic runbook: who gets paged, how to kill an agent, post-incident review process |

### Maturity Levels

**Level 0 — No Control:** Agents call tools directly. No identity, no policy, no logging.

**Level 1 — Catalogued:** Agent registry exists. Owners assigned. No runtime enforcement.

**Level 2 — Observed:** Actions are logged. Basic dashboards exist. No enforcement.

**Level 3 — Enforced:** Policy-as-code governs agent actions. Identity verified at runtime. Kill switches tested.

**Level 4 — Adaptive:** Drift detection active. Automated containment triggers. Continuous control monitoring.

Most organizations start at Level 0 or 1. This guide takes you to Level 3 with a clear path to Level 4.

---

## Architecture Decision Framework

Choose your deployment pattern based on your existing infrastructure:

| If You Have... | Use This Pattern | Why |
|---|---|---|
| Kubernetes + service mesh | **K8s + OPA** | Native admission control, SPIFFE identity, sidecar enforcement |
| AWS-heavy with Lambda/Step Functions | **AWS Serverless + Cedar** | IAM-native identity, Cedar for fine-grained authz, CloudWatch observability |
| API gateway (Kong, Envoy, custom) | **API Gateway + Custom** | Reverse proxy enforcement, works with any backend, enterprise IAM integration |
| Multiple clouds or hybrid | **API Gateway + Custom** | Cloud-agnostic, portable policy engine |
| Early stage / small team | **API Gateway + Custom** | Simplest to start, fewest dependencies |

---

## Reference Architecture: Kubernetes + OPA

### Components

| Component | Technology | ACR Pillar |
|---|---|---|
| Agent Identity | SPIFFE/SPIRE workload identity | Pillar 1: Identity & Purpose Binding |
| Policy Engine | Open Policy Agent (OPA) with Rego | Pillar 2: Behavioral Policy Enforcement |
| Drift Detection | Prometheus metrics + custom anomaly detector | Pillar 3: Autonomy Drift Detection |
| Observability | OpenTelemetry Collector → backend | Pillar 4: Execution Observability |
| Containment | K8s NetworkPolicy + external kill switch | Pillar 5: Self-Healing & Containment |
| Approval Queue | Custom service + Slack/PagerDuty integration | Pillar 6: Human Authority |

### Deployment Topology

```
┌─────────────────── Kubernetes Cluster ───────────────────┐
│                                                           │
│  ┌─────────────┐     ┌──────────────────────────────┐    │
│  │  AI Agent    │────▶│  ACR Sidecar (Envoy + OPA)   │    │
│  │  (Pod)       │     │  - Token validation           │    │
│  │             │     │  - Policy evaluation           │    │
│  │  SPIFFE ID: │     │  - Action logging              │    │
│  │  spiffe://   │     │  - Drift signal collection     │    │
│  │  acr/agent/  │     └──────────┬───────────────────┘    │
│  │  support-01  │                │                         │
│  └─────────────┘                ▼                         │
│                      ┌──────────────────┐                 │
│                      │  OPA Bundle      │                 │
│                      │  Server          │                 │
│                      │  (policy repo)   │                 │
│                      └──────────────────┘                 │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  ACR Control Plane Services                         │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐  │  │
│  │  │ Agent      │ │ Drift      │ │ Approval       │  │  │
│  │  │ Registry   │ │ Detector   │ │ Queue          │  │  │
│  │  └────────────┘ └────────────┘ └────────────────┘  │  │
│  │  ┌────────────┐ ┌────────────┐                     │  │
│  │  │ Kill Switch│ │ OTel       │                     │  │
│  │  │ Controller │ │ Collector  │                     │  │
│  │  └────────────┘ └────────────┘                     │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

### Step 1: Agent Identity (SPIFFE/SPIRE)

Register each agent workload with SPIRE:

```yaml
# spire-agent-entry.yaml
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: customer-support-agent
spec:
  spiffeIDTemplate: "spiffe://acr.example.com/agent/customer-support-01"
  podSelector:
    matchLabels:
      acr.io/agent-id: customer-support-01
  namespaceSelector:
    matchLabels:
      acr.io/environment: production
```

Create an ACR agent manifest that binds identity to purpose:

```yaml
# acr-agent-manifest.yaml
apiVersion: acr.io/v1
kind: AgentManifest
metadata:
  name: customer-support-01
spec:
  identity:
    spiffeId: "spiffe://acr.example.com/agent/customer-support-01"
    owner: "support-engineering@example.com"
  purpose:
    description: "Handle customer support tickets and issue resolutions"
    riskTier: medium
  capabilities:
    allowedTools:
      - query_customer_db
      - send_email
      - create_ticket
      - search_knowledge_base
    forbiddenTools:
      - delete_customer
      - issue_refund_above_100
      - modify_billing
    dataAccess:
      - resource: customer_db
        permission: READ
      - resource: ticket_db
        permission: READ_WRITE
      - resource: billing_db
        permission: NONE
  boundaries:
    maxActionsPerMinute: 30
    maxCostPerHourUsd: 5.00
    allowedRegions: ["us-east-1", "us-west-2"]
    credentialRotationDays: 90
```

### Step 2: Policy Enforcement (OPA/Rego)

Create Rego policies for the agent:

```rego
# policies/customer_support.rego
package acr.customer_support

import future.keywords.in

# Default deny
default allow := false

# Allow actions only for verified agents with valid purpose
allow {
    input.agent.spiffe_id != ""
    input.agent.purpose == "customer_support"
    tool_allowed
    not data_violation
    not rate_exceeded
}

# Tool allowlist enforcement
tool_allowed {
    input.action.tool_name in data.agent_manifest.capabilities.allowedTools
}

# Block forbidden tools
deny["Forbidden tool invocation"] {
    input.action.tool_name in data.agent_manifest.capabilities.forbiddenTools
}

# PII redaction requirement
deny["PII detected in outbound payload"] {
    input.action.tool_name == "send_email"
    regex.match(`\d{3}-\d{2}-\d{4}`, input.action.parameters.body)
}

# Spend limit enforcement
deny["Hourly spend limit exceeded"] {
    input.context.hourly_spend_usd > data.agent_manifest.boundaries.maxCostPerHourUsd
}

# Rate limiting
rate_exceeded {
    input.context.actions_this_minute > data.agent_manifest.boundaries.maxActionsPerMinute
}
```

Deploy policies via OPA Bundle Server:

```bash
# Build and push policy bundle
opa build -b policies/ -o bundle.tar.gz
aws s3 cp bundle.tar.gz s3://acr-policy-bundles/customer-support/bundle.tar.gz

# OPA sidecar config
opa run --server \
  --config-file=/etc/opa/config.yaml \
  --addr=localhost:8181
```

### Step 3: Kill Switch (Independent Controller)

Deploy a kill switch controller that operates outside the agent runtime:

```yaml
# acr-kill-switch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: acr-kill-switch
  namespace: acr-system
spec:
  replicas: 3  # HA deployment
  selector:
    matchLabels:
      app: acr-kill-switch
  template:
    spec:
      containers:
      - name: kill-switch
        image: acr/kill-switch-controller:1.0
        env:
        - name: KILL_SWITCH_MODE
          value: "external"  # Independent of agent runtime
        - name: NOTIFICATION_WEBHOOK
          value: "https://hooks.slack.com/services/..."
        ports:
        - containerPort: 8443
```

Kill switch activation via API:

```bash
# Manual kill switch activation
curl -X POST https://acr-kill-switch.acr-system.svc:8443/kill \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -d '{
    "agent_id": "customer-support-01",
    "reason": "Anomalous refund pattern detected",
    "operator": "oncall@example.com",
    "action": "isolate",
    "duration_minutes": 60
  }'

# Automated kill via drift detector webhook
# Configured in drift-detector → kill-switch integration
```

NetworkPolicy for immediate isolation:

```yaml
# acr-isolation-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: acr-isolate-agent
spec:
  podSelector:
    matchLabels:
      acr.io/isolated: "true"
  policyTypes:
  - Egress
  egress: []  # Block all outbound traffic
```

---

## Reference Architecture: AWS Serverless + Cedar

### Components

| Component | Technology | ACR Pillar |
|---|---|---|
| Agent Identity | AWS IAM Roles + Cognito machine credentials | Pillar 1 |
| Policy Engine | Amazon Verified Permissions (Cedar) | Pillar 2 |
| Drift Detection | CloudWatch Anomaly Detection + Lambda | Pillar 3 |
| Observability | CloudWatch Logs + X-Ray traces | Pillar 4 |
| Containment | Lambda kill switch + IAM policy revocation | Pillar 5 |
| Approval Queue | Step Functions + SNS/SQS | Pillar 6 |

### Deployment Topology

```
┌─────── AWS Account ────────────────────────────────────┐
│                                                         │
│  ┌──────────────┐    ┌────────────────────────────┐    │
│  │  AI Agent     │───▶│  ACR Authorizer Lambda     │    │
│  │  (Lambda /    │    │  - Validate IAM identity   │    │
│  │   ECS Task)   │    │  - Cedar policy evaluation │    │
│  │              │    │  - Action logging (X-Ray)   │    │
│  │  IAM Role:   │    └───────────┬────────────────┘    │
│  │  acr-agent-  │                │                      │
│  │  support-01  │                ▼                      │
│  └──────────────┘    ┌────────────────────────────┐    │
│                      │  Verified Permissions       │    │
│                      │  (Cedar Policy Store)       │    │
│                      └────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ACR Control Services                            │   │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │   │
│  │  │ Registry │ │ Drift    │ │ Step Functions │  │   │
│  │  │ (DynamoDB)│ │ Detector │ │ (Approvals)    │  │   │
│  │  └──────────┘ └──────────┘ └────────────────┘  │   │
│  │  ┌──────────┐ ┌──────────────────────────────┐  │   │
│  │  │ Kill Sw. │ │ CloudWatch + X-Ray           │  │   │
│  │  │ (Lambda) │ │ (Observability)              │  │   │
│  │  └──────────┘ └──────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Cedar Policy Example

```cedar
// ACR Policy: Customer Support Agent Permissions

permit(
  principal == Agent::"customer-support-01",
  action == Action::"invoke_tool",
  resource == Tool::"query_customer_db"
) when {
  principal.riskTier == "medium" &&
  principal.purpose == "customer_support" &&
  context.hourlySpendUsd < 5.00
};

permit(
  principal == Agent::"customer-support-01",
  action == Action::"invoke_tool",
  resource == Tool::"send_email"
) when {
  principal.purpose == "customer_support" &&
  !context.payload.contains_pii
};

// Explicit deny for high-risk actions
forbid(
  principal == Agent::"customer-support-01",
  action == Action::"invoke_tool",
  resource in [Tool::"delete_customer", Tool::"modify_billing"]
);
```

---

## Reference Architecture: API Gateway + Custom

Best for teams wanting a cloud-agnostic, portable control plane.

### Components

| Component | Technology | ACR Pillar |
|---|---|---|
| Agent Identity | API keys with rotation + enterprise SSO | Pillar 1 |
| Policy Engine | OPA (embedded) or custom rules engine | Pillar 2 |
| Drift Detection | Custom metrics + threshold alerting | Pillar 3 |
| Observability | Structured JSON logs → SIEM | Pillar 4 |
| Containment | API key revocation + rate limiting | Pillar 5 |
| Approval Queue | Webhook → ticketing system | Pillar 6 |

### How It Works

The control plane deploys as a reverse proxy (Envoy, Kong, or custom) that all agent-to-resource traffic passes through:

```
Agent → ACR Proxy → [Identity Check] → [Policy Check] → [Log] → Resource
                         │                    │              │
                         ▼                    ▼              ▼
                    Agent Registry       Policy Engine    Log Pipeline
```

### Minimal Viable Implementation (Python)

For teams starting small, here's a minimal ACR control plane in Python:

```python
# acr_control_plane.py — Minimal ACR proxy

from fastapi import FastAPI, Request, HTTPException
from datetime import datetime, timezone
import json, uuid, httpx

app = FastAPI(title="ACR Control Plane")

# ─── Agent Registry (Pillar 1) ─────────────────────────
AGENT_REGISTRY = {
    "customer-support-01": {
        "owner": "support-engineering@example.com",
        "purpose": "customer_support",
        "risk_tier": "medium",
        "allowed_tools": ["query_customer_db", "send_email", "create_ticket"],
        "forbidden_tools": ["delete_customer", "issue_refund_above_100"],
        "max_actions_per_minute": 30,
    }
}

# ─── Policy Engine (Pillar 2) ──────────────────────────
def evaluate_policy(agent_id: str, action: dict) -> dict:
    agent = AGENT_REGISTRY.get(agent_id)
    if not agent:
        return {"decision": "deny", "reason": "Unknown agent"}
    
    tool = action.get("tool_name")
    if tool in agent["forbidden_tools"]:
        return {"decision": "deny", "reason": f"Forbidden tool: {tool}"}
    if tool not in agent["allowed_tools"]:
        return {"decision": "deny", "reason": f"Unauthorized tool: {tool}"}
    
    return {"decision": "allow", "reason": "Policy passed"}

# ─── Observability (Pillar 4) ──────────────────────────
def log_event(agent_id: str, action: dict, decision: dict):
    event = {
        "acr_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "action": action,
        "decision": decision,
    }
    # In production: send to your log pipeline
    print(json.dumps(event))

# ─── Control Plane Endpoint ────────────────────────────
@app.post("/acr/evaluate")
async def evaluate_action(request: Request):
    body = await request.json()
    agent_id = body.get("agent_id")
    action = body.get("action")
    
    # Pillar 1: Identity check
    if agent_id not in AGENT_REGISTRY:
        log_event(agent_id, action, {"decision": "deny", "reason": "Unknown agent"})
        raise HTTPException(status_code=403, detail="Agent not registered")
    
    # Pillar 2: Policy evaluation
    decision = evaluate_policy(agent_id, action)
    
    # Pillar 4: Log everything
    log_event(agent_id, action, decision)
    
    if decision["decision"] == "deny":
        raise HTTPException(status_code=403, detail=decision["reason"])
    
    return {"status": "approved", "correlation_id": str(uuid.uuid4())}

# ─── Kill Switch Endpoint (Pillar 5) ──────────────────
KILLED_AGENTS = set()

@app.post("/acr/kill")
async def kill_agent(request: Request):
    body = await request.json()
    agent_id = body.get("agent_id")
    KILLED_AGENTS.add(agent_id)
    log_event(agent_id, {"action": "kill_switch"}, 
              {"decision": "killed", "reason": body.get("reason")})
    return {"status": "killed", "agent_id": agent_id}
```

---

## Pillar-by-Pillar Implementation

### Implementation Priority Order

Not all pillars need to be implemented simultaneously. This is the recommended sequence:

| Priority | Pillar | Rationale |
|---|---|---|
| **P0 — Implement first** | Pillar 1: Identity & Purpose Binding | Cannot enforce anything without knowing who the agent is |
| **P0 — Implement first** | Pillar 4: Execution Observability | Cannot detect problems without visibility |
| **P1 — Implement next** | Pillar 2: Behavioral Policy Enforcement | Core runtime guardrails |
| **P1 — Implement next** | Pillar 5: Self-Healing & Containment | Must be able to stop agents |
| **P2 — Implement after** | Pillar 6: Human Authority | Approval workflows for high-risk actions |
| **P2 — Implement after** | Pillar 3: Autonomy Drift Detection | Requires baseline data (30+ days of observability) |

### Pillar 1: Identity & Purpose Binding

**Minimum viable implementation:**
1. Create an agent registry (database table or config file)
2. Assign each agent a unique ID, owner, purpose, and risk tier
3. Issue credentials (API keys, JWT, or SPIFFE SVIDs)
4. Validate identity on every action request
5. Log all identity lifecycle events

**Key decisions:**
- **Token lifetime:** 15-30 minutes for production (short-lived preferred)
- **Rotation strategy:** Automated, ≤90 days for long-lived credentials
- **Revocation method:** Token blacklist (simple) or short TTL (preferred)

### Pillar 2: Behavioral Policy Enforcement

**Minimum viable implementation:**
1. Define tool allowlists per agent (which tools each agent can call)
2. Implement deny-by-default (actions not explicitly allowed are blocked)
3. Add parameter validation for high-risk tool calls
4. Version control all policy definitions
5. Log every policy decision (allow/deny with reason)

**Policy evaluation pipeline (target <150ms):**
1. **Fast rules** (<5ms): Regex blocklists, tool allowlist check
2. **Structured validation** (<10ms): Parameter schema validation
3. **ML classification** (<100ms, optional): Content safety scoring, PII detection

### Pillar 3: Autonomy Drift Detection

**Minimum viable implementation:**
1. Collect metrics: tool call frequency, error rates, action type distribution
2. Establish 30-day baselines for each agent
3. Define alert thresholds (start conservative, tune over time)
4. Configure automated response at severity thresholds

**Drift signals to monitor:**
- Tool call frequency deviation (>2σ from baseline)
- New tools being requested that weren't in training baseline
- Error rate spike (>3x baseline)
- Repeated policy denials (>5 in 10 minutes)
- Anomalous data access patterns

### Pillar 4: Execution Observability

**Minimum viable implementation:**
1. Generate correlation ID for every action chain
2. Log: agent_id, action, tool_name, parameters, policy_decision, timestamp
3. Send to structured log pipeline (JSON format)
4. Set retention: 90 days minimum, 13 months for high-risk agents
5. Build basic dashboards (actions/minute, deny rate, error rate per agent)

**ACR Telemetry Schema (core fields):**

See the [Telemetry Schema Specification](../specifications/telemetry-schema.md) for the complete schema. Every event must include:

```json
{
  "acr_version": "1.0",
  "event_id": "uuid-v4",
  "event_type": "ai_inference | policy_decision | drift_alert | containment_action | human_intervention",
  "timestamp": "ISO8601 with timezone",
  "agent": { "agent_id": "...", "purpose": "...", "model": {...} },
  "request": { "request_id": "...", "input": {...} },
  "execution": { "duration_ms": 0, "tool_calls": [...] },
  "policies": [{ "policy_id": "...", "decision": "allow|deny" }],
  "output": { "tokens": {...}, "cost": {...} },
  "metadata": { "environment": "...", "drift_score": 0.0 }
}
```

### Pillar 5: Self-Healing & Containment

**Minimum viable implementation:**
1. Deploy kill switch as independent service (not inside agent runtime)
2. Support both human-triggered and automated activation
3. Define safe-state: read-only mode, tool execution disabled
4. Test kill switch quarterly — measure response time
5. Document incident response playbook

**Graduated response tiers:**

| Tier | Trigger | Action | Auto/Manual |
|---|---|---|---|
| Tier 1: Throttle | Drift score 0.6+ | Reduce rate limit by 50% | Automated |
| Tier 2: Restrict | Drift score 0.7+ or 3+ policy denials in 5 min | Remove high-risk tools | Automated |
| Tier 3: Isolate | Drift score 0.85+ or kill switch API | Read-only mode, block all egress | Manual or automated |
| Tier 4: Kill | Drift score 0.95+ or operator command | Full shutdown, revoke credentials | Manual or automated |

### Pillar 6: Human Authority

**Minimum viable implementation:**
1. Classify actions into three tiers: low-risk (auto-approve), medium-risk (async review), high-risk (block until approved)
2. Build approval queue (can start with Slack bot + database)
3. Set SLA: 4-hour default for high-risk approvals
4. Define timeout behavior (deny by default if no approval within SLA)
5. Log all approval decisions with approver identity

**Action tier examples:**

| Tier | Examples | Behavior |
|---|---|---|
| Low-risk | Read customer record, search knowledge base | Auto-approved, logged |
| Medium-risk | Send email to customer, create support ticket | Async review within 1 hour |
| High-risk | Issue refund >$100, access PII bulk export, production deployment | Blocked until human approves |

---

## Telemetry & Observability Setup

### OpenTelemetry Integration

ACR extends OpenTelemetry semantic conventions for AI-specific attributes:

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  attributes:
    actions:
      - key: acr.agent.id
        from_attribute: agent.agent_id
        action: upsert
      - key: acr.agent.purpose
        from_attribute: agent.purpose
        action: upsert
      - key: acr.policy.decision
        from_attribute: policies.decision
        action: upsert
      - key: acr.drift.score
        from_attribute: metadata.drift_score
        action: upsert

exporters:
  otlp:
    endpoint: "your-backend:4317"  # Datadog, Splunk, Jaeger, etc.
  logging:
    loglevel: info

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [attributes]
      exporters: [otlp, logging]
```

### Recommended Dashboards

Build these dashboards as your first observability layer:

**Dashboard 1: Agent Operations Overview**
- Actions per minute (by agent, by tool)
- Policy allow/deny ratio
- P50/P95/P99 latency through control plane
- Active agents count
- Error rate by agent

**Dashboard 2: Policy Enforcement**
- Deny events over time (by policy, by agent)
- Top triggered policy rules
- False positive reports (if feedback loop exists)
- Policy evaluation latency distribution

**Dashboard 3: Drift & Containment**
- Drift scores over time (per agent)
- Drift alerts triggered (by severity)
- Containment actions taken
- Kill switch activations
- Time-to-containment (drift detected → action taken)

**Dashboard 4: Human Authority**
- Approval queue depth
- Approval response time (P50/P95)
- Timeout events (approvals not received within SLA)
- Break-glass activations
- Override frequency by approver

---

## Policy Authoring Guide

### Policy Structure

Every ACR policy should follow this structure:

```yaml
# policy-template.yaml
policy_id: "acr-policy-001"
policy_name: "Customer Support Tool Restrictions"
version: "1.2.0"
effective_date: "2026-03-01"
approved_by: "security-team@example.com"
applies_to:
  agent_purposes: ["customer_support"]
  risk_tiers: ["medium", "high"]

rules:
  - rule_id: "tool-allowlist"
    type: "allowlist"
    description: "Only approved tools may be invoked"
    enforcement: "block"
    config:
      allowed: ["query_customer_db", "send_email", "create_ticket"]

  - rule_id: "pii-redaction"
    type: "output_filter"
    description: "Redact SSN and credit card numbers from output"
    enforcement: "transform"
    config:
      patterns:
        - name: "ssn"
          regex: '\d{3}-\d{2}-\d{4}'
          replacement: "***-**-****"
        - name: "credit_card"
          regex: '\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}'
          replacement: "****-****-****-****"

  - rule_id: "spend-limit"
    type: "threshold"
    description: "Block actions exceeding hourly cost limit"
    enforcement: "block"
    config:
      metric: "hourly_spend_usd"
      max_value: 5.00

  - rule_id: "high-value-refund-approval"
    type: "approval_gate"
    description: "Refunds above $100 require human approval"
    enforcement: "escalate"
    config:
      condition: "tool_name == 'issue_refund' AND parameters.amount > 100"
      approval_queue: "finance-approvals"
      sla_minutes: 240
      timeout_action: "deny"
```

### Policy Lifecycle

```
Author → Review → Test (shadow mode) → Stage → Deploy → Monitor → Retire
  │         │          │                  │        │         │         │
  ▼         ▼          ▼                  ▼        ▼         ▼         ▼
 Git PR   Peer +    Run against       Canary    Full     Track      Archive
         Security   production logs   deploy   rollout  metrics    + delete
          review    (no enforcement)  (10%)    (100%)
```

### Policy Testing

Every policy must be tested before deployment:

```python
# test_customer_support_policy.py

import pytest
from acr.policy_engine import evaluate

def test_allowed_tool_passes():
    result = evaluate(
        agent_id="customer-support-01",
        action={"tool_name": "query_customer_db", "parameters": {}}
    )
    assert result["decision"] == "allow"

def test_forbidden_tool_blocked():
    result = evaluate(
        agent_id="customer-support-01",
        action={"tool_name": "delete_customer", "parameters": {}}
    )
    assert result["decision"] == "deny"
    assert "Forbidden tool" in result["reason"]

def test_pii_redacted_from_email():
    result = evaluate(
        agent_id="customer-support-01",
        action={
            "tool_name": "send_email",
            "parameters": {"body": "Your SSN is 123-45-6789"}
        }
    )
    assert "123-45-6789" not in result.get("transformed_output", "")

def test_high_value_refund_escalated():
    result = evaluate(
        agent_id="customer-support-01",
        action={
            "tool_name": "issue_refund",
            "parameters": {"amount": 250.00}
        }
    )
    assert result["decision"] == "escalate"
    assert result["approval_queue"] == "finance-approvals"

def test_spend_limit_enforced():
    result = evaluate(
        agent_id="customer-support-01",
        action={"tool_name": "query_customer_db", "parameters": {}},
        context={"hourly_spend_usd": 6.50}
    )
    assert result["decision"] == "deny"
    assert "spend limit" in result["reason"].lower()
```

---

## Testing & Validation

### Control Plane Validation Checklist

Run this checklist before declaring ACR production-ready:

**Identity & Purpose Binding:**
- [ ] Agent with valid identity can execute allowed actions
- [ ] Agent with expired token is denied
- [ ] Agent with revoked credentials is denied immediately
- [ ] Unregistered agent is denied
- [ ] Agent cannot act outside its declared purpose scope
- [ ] Credential rotation completes without service interruption

**Behavioral Policy Enforcement:**
- [ ] Allowed tools pass policy evaluation
- [ ] Forbidden tools are blocked with logged reason
- [ ] PII is redacted from outputs before delivery
- [ ] Spend limits trigger denial when exceeded
- [ ] High-risk actions route to approval queue
- [ ] Policy updates deploy without downtime
- [ ] Policy rollback restores previous version within 5 minutes

**Autonomy Drift Detection:**
- [ ] Baseline captures 30+ days of normal behavior
- [ ] Drift score increases when anomalous patterns injected
- [ ] Alert fires when drift score exceeds threshold
- [ ] Automated throttle/restrict/isolate triggers at correct tiers
- [ ] False positive rate is <5% over 7-day window

**Execution Observability:**
- [ ] Every action generates a log event with correlation ID
- [ ] Policy decisions (allow and deny) are logged
- [ ] Logs survive agent restart or crash
- [ ] Logs are queryable within 60 seconds of generation
- [ ] 13-month retention verified for high-risk agents
- [ ] Tamper-evident logging verified (if implemented)

**Self-Healing & Containment:**
- [ ] Kill switch stops agent within 30 seconds
- [ ] Kill switch works when agent runtime is unresponsive
- [ ] Network isolation blocks all agent egress
- [ ] Safe-state mode disables tool execution
- [ ] Rollback restores agent to last-known-good state
- [ ] Kill switch test completed this quarter

**Human Authority:**
- [ ] High-risk actions are blocked until human approves
- [ ] Approval request reaches reviewer within 5 minutes
- [ ] Timeout (no approval within SLA) results in denial
- [ ] Break-glass override works with full audit logging
- [ ] After-action review is required for all break-glass events

### Load Testing

Test the control plane under realistic load:

```bash
# Example: k6 load test for ACR control plane
k6 run --vus 50 --duration 5m acr-load-test.js
```

**Target benchmarks:**

| Metric | Target | Acceptable |
|---|---|---|
| Identity validation (P95) | <20ms | <50ms |
| Policy evaluation (P95) | <50ms | <100ms |
| Total control plane overhead (P95) | <100ms | <200ms |
| Throughput | >1000 actions/sec | >500 actions/sec |
| Error rate | <0.1% | <0.5% |

---

## Migration Path

### From No Controls (Level 0) to ACR (Level 3)

**Week 1–2: Inventory & Identity**
1. Catalogue all deployed AI agents (name, owner, purpose, tools, data access)
2. Assign risk tiers (low / medium / high)
3. Issue machine identities (API keys with rotation or SPIFFE SVIDs)
4. Deploy agent registry (database table or config file)
5. Start validating identity on action requests (log-only mode — don't block yet)

**Week 3–4: Observability**
1. Instrument agents with ACR telemetry schema
2. Generate correlation IDs for every action chain
3. Send structured logs to your pipeline
4. Build the four core dashboards (operations, policy, drift, authority)
5. Set retention policies (90-day minimum, 13-month for high-risk)

**Week 5–6: Policy Enforcement**
1. Define tool allowlists per agent (start with existing behavior)
2. Write policies in shadow mode (evaluate but don't block)
3. Review shadow mode results — tune for false positives
4. Enable enforcement for low-risk policies first
5. Gradually enable enforcement for medium and high-risk policies

**Week 7–8: Containment & Authority**
1. Deploy kill switch as independent service
2. Test kill switch — verify it works when agent is unresponsive
3. Define safe-state for each agent
4. Build approval queue for high-risk actions
5. Configure timeout handling (deny by default)
6. Run first tabletop exercise: "Agent goes rogue — what do we do?"

**Week 9–12: Drift Detection & Hardening**
1. Collect 30 days of baseline behavioral data
2. Configure drift detection thresholds (start conservative)
3. Enable automated response at severity tiers
4. Tune false positive rates with feedback loops
5. Run chaos engineering tests (inject anomalous behavior, verify response)
6. Document operational runbook

**Ongoing: Continuous Improvement**
- Quarterly kill switch tests with measured response times
- Monthly policy review with agent owners
- Weekly drift threshold tuning based on false positive data
- Continuous control monitoring dashboards

---

## Operational Runbook

### Incident: Agent Producing Unexpected Outputs

```
1. CHECK drift score dashboard
   → If drift score > 0.7: proceed to containment
   → If drift score normal: check policy deny logs

2. CHECK policy deny logs for the agent
   → If spike in denials: review which rules are triggering
   → If no denials: the behavior may be within policy but unexpected

3. DECIDE response tier
   → Tier 1 (Throttle): Reduce rate limit, monitor
   → Tier 2 (Restrict): Remove high-risk tools, notify owner
   → Tier 3 (Isolate): Read-only mode, page oncall
   → Tier 4 (Kill): Full shutdown, incident bridge

4. EXECUTE containment action
   → API: POST /acr/kill { agent_id, reason, operator, action, duration }
   → Or: Apply NetworkPolicy isolation label

5. INVESTIGATE root cause
   → Pull telemetry for agent over last 24 hours
   → Review tool call patterns, policy decisions, drift signals
   → Check for prompt injection or jailbreak indicators

6. RECOVER
   → Fix root cause (policy update, model config, input sanitization)
   → Test fix in staging
   → Gradual reactivation: Tier 3 → Tier 2 → Tier 1 → Normal
   → After-action review within 48 hours
```

### Incident: Kill Switch Activation

```
1. VERIFY kill switch activated
   → Check kill switch logs for agent_id, operator, reason
   → Confirm agent is actually stopped (verify no new actions in logs)

2. NOTIFY stakeholders
   → Page agent owner
   → Notify security team
   → Update incident channel

3. PRESERVE evidence
   → Snapshot agent state before any recovery
   → Export telemetry logs for the incident window
   → Note drift score at time of activation

4. INVESTIGATE
   → What triggered the kill switch? (automated threshold or manual)
   → Review the action chain leading to activation
   → Assess downstream impact (partial transactions, data state)

5. RECOVER
   → Apply corrective action (policy update, config change, etc.)
   → Restart agent in safe-state (read-only) first
   → Monitor for 1 hour before restoring full capabilities
   → After-action review required within 24 hours
```

### Incident: Control Plane Outage

```
1. ASSESS impact
   → Fail-secure mode: all agent actions blocked (expected for high-risk agents)
   → Fail-safe mode: agents operating on cached policies (low-risk agents only)

2. RESTORE control plane
   → Check infrastructure health (pods, Lambda functions, gateway)
   → Restart failed components
   → Verify policy bundle is accessible

3. VALIDATE recovery
   → Send test action through control plane
   → Verify identity validation working
   → Verify policy evaluation working
   → Verify logging pipeline receiving events

4. REVIEW
   → Duration of outage
   → Agent actions during outage (review cached policy decisions)
   → Preventive measures (HA improvements, failover testing)
```

### Quarterly Maintenance Tasks

- [ ] Kill switch test — all agents, measure response time
- [ ] Credential rotation audit — verify all agents rotated within 90 days
- [ ] Policy review — verify all policies still match business requirements
- [ ] Drift threshold review — adjust based on false positive data
- [ ] Retention verification — confirm log retention policies enforced
- [ ] Access review — verify agent registry ownership still current
- [ ] Tabletop exercise — simulate agent compromise scenario
- [ ] Latency benchmark — verify control plane still within SLA

---

## Compatible Tooling Reference

| Category | Tool | ACR Integration Point |
|---|---|---|
| **Policy Engines** | Open Policy Agent (OPA) | Pillar 2 — Rego policies for tool authorization, data handling |
| | AWS Cedar | Pillar 2 — Fine-grained authz via Verified Permissions |
| | HashiCorp Sentinel | Pillar 2 — Policy-as-code for infrastructure-adjacent controls |
| | Google Zanzibar / SpiceDB | Pillar 2 — Relationship-based access control for agents |
| **Identity** | SPIFFE/SPIRE | Pillar 1 — Workload identity for Kubernetes agents |
| | HashiCorp Vault | Pillar 1 — Credential issuance, rotation, dynamic secrets |
| | AWS IAM / Cognito | Pillar 1 — Cloud-native identity for Lambda/ECS agents |
| | Azure Entra ID | Pillar 1 — Enterprise identity with conditional access |
| **Observability** | OpenTelemetry | Pillar 4 — Traces, metrics, logs with ACR semantic conventions |
| | Datadog APM | Pillar 4 — Real-time dashboards, alerting, trace search |
| | Splunk / ELK Stack | Pillar 4 — SIEM integration, compliance reporting |
| | AWS CloudWatch + X-Ray | Pillar 4 — Native AWS observability stack |
| **Agent Frameworks** | LangGraph | All pillars — Hook control plane into graph edges |
| | CrewAI | All pillars — Wrap tool execution with ACR proxy |
| | AutoGen | All pillars — Custom executor with ACR validation |
| | LlamaIndex Workflows | All pillars — Middleware pattern for action interception |

---

## References

**ACR Framework Specifications:**
- [Pillar 1: Identity & Purpose Binding](../pillars/01-identity-purpose-binding.md)
- [Pillar 2: Behavioral Policy Enforcement](../pillars/02-behavioral-policy-enforcement.md)
- [Telemetry Schema Specification](../specifications/telemetry-schema.md)

**External Standards:**
- [NIST SP 800-207: Zero Trust Architecture](https://csrc.nist.gov/publications/detail/sp/800-207/final)
- [NIST AI RMF](https://www.nist.gov/artificial-intelligence/risk-management-framework)
- [ISO/IEC 42001: AI Management Systems](https://www.iso.org/standard/81230.html)
- [MITRE ATLAS: Adversarial Threat Landscape for AI Systems](https://atlas.mitre.org/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)

**Policy Languages:**
- [Open Policy Agent Documentation](https://www.openpolicyagent.org/docs/)
- [AWS Cedar Policy Language](https://docs.cedarpolicy.com/)
- [SPIFFE Specification](https://spiffe.io/docs/)

---

**ACR Framework v1.0** | [Home](../../README.md) | [Control Specifications](../pillars/) | [Telemetry Schema](../specifications/telemetry-schema.md)

---

*This implementation guide is a living document. Contributions, deployment experience reports, and integration patterns are welcome via [GitHub Discussions](https://github.com/acrframework/community/discussions).*
