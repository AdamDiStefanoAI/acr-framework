# ACR Standard Glossary

This glossary defines key terminology used within the ACR Standard and related governance models.

---

# ACR Control Plane

The runtime governance layer responsible for mediating interactions between autonomous AI systems and enterprise infrastructure.

The control plane enforces governance policies, monitors system behavior, and enables intervention when necessary.

---

# Autonomous AI System

An AI system capable of performing actions, executing workflows, or interacting with enterprise resources without direct human instruction at each step.

Examples include:

- AI agents
- autonomous workflow systems
- enterprise copilots
- multi-agent orchestration systems

---

# Behavioral Policy Enforcement

The process of translating organizational AI governance policies into machine-enforceable runtime controls that restrict AI system actions.

---

# Execution Observability

The capability to monitor and record AI system inputs, actions, and outputs during runtime.

Observability enables auditing, investigation, and governance oversight.

---

# Identity & Purpose Binding

A governance mechanism that assigns an AI system a defined identity and operational purpose.

This prevents AI systems from operating outside their authorized scope.

---

# Autonomy Drift

The gradual divergence of an AI system's behavior from its intended operational boundaries.

Drift may occur as systems interact with new inputs, tools, or workflows.

---

# Drift Detection

A monitoring capability that identifies abnormal AI system behavior or deviations from expected execution patterns.

---

# Tool Access Gateway

A governance mechanism that mediates AI interactions with enterprise tools, APIs, and services.

This ensures that AI systems only access authorized resources.

---

# Containment Controls

Automated mechanisms used to limit the impact of abnormal or unsafe AI behavior.

Examples include:

- capability restriction
- workflow interruption
- system isolation

---

# Human Authority

The principle that human operators retain ultimate decision authority over autonomous AI systems.

Human oversight mechanisms allow operators to intervene, override, or terminate AI system execution.

---

# STRIKE Framework

A threat model describing security risks associated with autonomous AI systems.

STRIKE identifies six threat categories:

- Scope Escalation
- Tool Misuse
- Role Drift
- Information Leakage
- Kill Chain Expansion
- Execution Manipulation

---

# Runtime Governance

Governance mechanisms that remain active while AI systems operate in production environments.

Runtime governance enables organizations to enforce policies, monitor behavior, and intervene in system activity.

---

# Agentic Control at Runtime (ACR)

A governance framework designed to manage the behavior of autonomous AI systems operating in enterprise environments.

ACR introduces runtime control architecture that enforces governance policies while AI systems are actively executing.

---

# Control Layer / Pillar

Within ACR, the six control layers (Identity & Purpose Binding, Behavioral Policy Enforcement, Autonomy Drift Detection, Execution Observability, Self-Healing & Containment, Human Authority) are also called **pillars**. Each pillar has a full specification document with control objectives, patterns, and evaluation criteria.

---

# Policy Engine

A component that evaluates requests, actions, or outputs against a set of rules (policies). In ACR, the Behavioral Policy Enforcement layer typically uses a policy engine (e.g. OPA, Cedar) to enforce allowlists, denylists, input/output filters, and action authorization.

---

# Telemetry Schema

The canonical structure for events emitted by an ACR control plane. Defined in the [Telemetry Schema Specification](../specifications/telemetry-schema.md). Events include agent identity, request/execution context, policy decisions, and metadata (e.g. drift score). Used for audit, drift detection, and compliance evidence.

---

# Kill Switch

A mechanism to immediately halt or isolate an AI system (e.g. revoke credentials, block egress, stop processing). ACR recommends deploying the kill switch independently of the agent runtime so it remains available even if the agent is compromised. See [Self-Healing & Containment](../pillars/05-self-healing-containment.md).

---

# Break-Glass

An override that allows a human operator to permit an action that would otherwise be denied by policy, typically for emergencies or exceptional cases. Break-glass use should be logged and reviewed. Part of the Human Authority pillar.

---

# Purpose Binding

The association of an AI system with a specific operational purpose (e.g. `customer_support`, `data_analysis`). Purpose restricts which tools, data, and actions the system is allowed to use. Enforced by the Identity & Purpose Binding layer.

---

# STRIKE (mnemonic)

The six threat categories in the ACR/STRIKE threat model: **S**cope Escalation, **T**ool Misuse, **R**ole Drift, **I**nformation Leakage, **K**ill Chain Expansion, **E**xecution Manipulation. Used for risk assessment and mapping controls to threats. See [STRIKE Threat Model](./acr-strike-threat-model.md).

---

# ACR Maturity Level

A staged adoption level (1, 2, or 3) indicating how many ACR pillars are implemented. Level 1: Observability & Policy. Level 2: + Drift Detection & Containment. Level 3: All six pillars. See [ADOPTION.md](../../ADOPTION.md).
