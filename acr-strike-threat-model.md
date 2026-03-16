# STRIKE Threat Model for Autonomous AI Systems

The STRIKE Framework defines a threat model for autonomous AI systems.

While the ACR Framework provides governance controls and runtime architecture, STRIKE defines the primary risk categories that those controls are designed to mitigate.

Together, STRIKE and ACR form a complementary model:

- STRIKE → Threat identification
- ACR → Governance and control architecture

---

# STRIKE Threat Categories

STRIKE identifies six classes of risk that emerge as AI systems become increasingly autonomous and capable of interacting with enterprise systems.

## S — Scope Escalation

An AI system gains access to capabilities, tools, or data outside its approved operational scope.

Examples:

- accessing unauthorized systems
- invoking privileged APIs
- interacting with restricted datasets

Relevant ACR Controls:

- Identity & Purpose Binding
- Behavioral Policy Enforcement

---

## T — Tool Misuse

Autonomous agents misuse available tools or APIs in unintended ways.

Examples:

- executing unintended system actions
- sending unauthorized communications
- triggering financial transactions

Relevant ACR Controls:

- Behavioral Policy Enforcement
- Human Authority

---

## R — Role Drift

An AI system gradually diverges from its intended operational role.

Examples:

- expanding task scope
- making decisions beyond its authority
- interacting with systems outside its intended domain

Relevant ACR Controls:

- Autonomy Drift Detection
- Identity & Purpose Binding

---

## I — Information Leakage

Sensitive data is exposed through AI outputs or system interactions.

Examples:

- leaking PII or confidential information
- exposing internal data sources
- unauthorized model access to sensitive data

Relevant ACR Controls:

- Behavioral Policy Enforcement
- Execution Observability

---

## K — Kill Chain Expansion

AI systems can inadvertently extend the attack surface of enterprise environments.

Examples:

- enabling automated lateral movement
- exposing additional attack pathways
- chaining actions across systems

Relevant ACR Controls:

- Self-Healing & Containment
- Behavioral Policy Enforcement

---

## E — Execution Manipulation

Adversaries influence AI behavior through prompts, inputs, or system interactions.

Examples:

- prompt injection
- adversarial instructions
- manipulation of AI decision processes

Relevant ACR Controls:

- Execution Observability
- Autonomy Drift Detection
- Human Authority

---

# STRIKE + ACR Model

Together, STRIKE and ACR provide a complete governance model for autonomous AI systems.
