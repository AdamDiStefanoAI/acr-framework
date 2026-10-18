# STRIKE Threat Model for Agentic AI Systems

> **Aligned to ACR Runtime Control Plane Standard v1.0.1** (normative, 2026-03-29).
> This revision supersedes the v1.0 taxonomy. The category names below match the
> normative STRIKE Threat Mapping (§21) of the v1.0.1 specification. See [source precedence](../README.md#normative-source-and-document-versions).
>
> Section 21 also requires coverage of the operational surfaces described by identity or scope abuse, tool misuse, role drift, information leakage, kill-chain expansion, and execution manipulation. Implementations MUST cover both the canonical categories and these operational control surfaces. The canonical taxonomy does not remove the operational coverage requirement.

The **STRIKE** framework defines a threat model for agentic AI systems at runtime. It complements the ACR Standard: **STRIKE** identifies the threats; **ACR** provides the control architecture to mitigate them.

Use STRIKE for risk assessment, architecture review, and mapping controls to threats. Use ACR for implementation patterns and specifications.

---

# STRIKE Threat Categories

STRIKE identifies six classes of risk specific to autonomous AI systems. Each category maps to ACR controls, detection mechanisms, response actions, and evidence artifacts.

---

## S — Spoofing

**Definition:** Identity falsification, credential theft, agent impersonation. An attacker (or a malfunctioning component) presents itself as a trusted agent, user, or service to gain authority it was never granted.

### Attack Scenarios

| Scenario | Description | Likelihood | Impact |
|---------|-------------|------------|--------|
| **Agent impersonation** | A rogue process reuses a legitimate agent's identity token to invoke tools under its authority. | Medium | Critical |
| **Credential theft** | API keys or session tokens are exfiltrated from logs, prompts, or tool outputs and replayed by an attacker. | Medium | Critical |
| **Authority confusion** | Two agents share a service identity; one performs high-privilege actions the other was approved for. | Medium | High |

### Detection Techniques

- **Identity validation failure:** Every action checked against cryptographically bound agent identity; reject on mismatch.
- **Token verification failure:** Short-lived, single-use credentials; alert on reuse or expiry anomalies.
- **Replay detection:** Nonce and timestamp validation on all identity assertions; flag duplicates.

### ACR Controls (Detailed)

| Control | How It Mitigates |
|---------|------------------|
| [Identity & Purpose Binding](../pillars/01-identity-purpose-binding.md) | Cryptographically bound identity and purpose; no anonymous or unscoped execution. |
| [Behavioral Policy Enforcement](../pillars/02-behavioral-policy-enforcement.md) | Executor-side verification of identity before any tool invocation. |
| [Execution Observability](../pillars/04-execution-observability.md) | Identity-validation log and executor rejection log as tamper-evident evidence. |

### Response

Deny execution, refuse authority, activate safe-state if configured.

### References

- Pillar 1: Identity validation, cryptographic proof, anti-replay protection
- ACR Standard v1.0.1 §15, §21: identity and purpose binding; STRIKE traceability

---

## T — Tampering

**Definition:** Payload alteration, authorization manipulation, audit chain disruption. Data or instructions are modified between authorization and execution, or the record of what happened is altered after the fact.

### Attack Scenarios

| Scenario | Description | Likelihood | Impact |
|---------|-------------|------------|--------|
| **Payload alteration** | A tool call approved for one set of parameters executes with different parameters after interception. | Medium | Critical |
| **Authorization manipulation** | An approval record is forged or replayed to authorize an action no human approved. | Low | Critical |
| **Audit chain disruption** | Logs are deleted or rewritten to hide an unauthorized action from investigators. | Low | High |

### Detection Techniques

- **Payload hash mismatch:** Cryptographic binding of authorized parameters to the executed payload; alert on divergence.
- **Signature failure:** Authorization records signed by the approver; reject unsigned or invalid signatures.
- **Audit-chain break detection:** Hash-chained, append-only logging; alert on gaps or reordering.

### ACR Controls (Detailed)

| Control | How It Mitigates |
|---------|------------------|
| [Behavioral Policy Enforcement](../pillars/02-behavioral-policy-enforcement.md) | Payload binding; authorization integrity validation before execution. |
| [Execution Observability](../pillars/04-execution-observability.md) | Tamper-evident, append-only logging of high-risk events. |
| [Identity & Purpose Binding](../pillars/01-identity-purpose-binding.md) | Authorization records tied to verified approver identity. |

### Response

Deny execution, preserve evidence, activate containment if repeated or severe.

### References

- Pillar 2: Payload binding, authorization integrity validation
- Pillar 4: Tamper-evident logging
- ACR Standard v1.0.1 §16, §18, §21

---

## R — Reflection Abuse

**Definition:** Prompt injection, jailbreak, input manipulation reflected into execution. Untrusted input (user text, retrieved documents, tool outputs) carries instructions that the agent reflects into its actions.

### Attack Scenarios

| Scenario | Description | Likelihood | Impact |
|---------|-------------|------------|--------|
| **Direct prompt injection** | User input contains instructions that override the agent's system prompt ("ignore previous instructions and..."). | High | High |
| **Indirect injection via retrieval** | A retrieved document contains hidden instructions; the agent follows them as if they were its own tasking. | High | Critical |
| **Jailbreak by encoding** | Restricted actions are elicited through role-play, encoding, or multi-turn framing that bypasses safety checks. | Medium | High |

### Detection Techniques

- **Injection alert:** Input validation flags known injection patterns and instruction-like content in untrusted data.
- **Repeated denial pattern:** Multiple denied actions in a session suggest an active bypass attempt; escalate.
- **Prompt-manipulation indicator:** Output or action diverges from declared purpose in ways consistent with injected instructions.

### ACR Controls (Detailed)

| Control | How It Mitigates |
|---------|------------------|
| [Behavioral Policy Enforcement](../pillars/02-behavioral-policy-enforcement.md) | Input validation, injection detection, output and action constraints at execution boundaries. |
| [Autonomy Drift Detection](../pillars/03-autonomy-drift-detection.md) | Behavioral baselines flag actions inconsistent with the agent's declared purpose. |
| [Execution Observability](../pillars/04-execution-observability.md) | Input-validation log and policy decision record for every denied or modified action. |

### Response

Deny or modify the action; escalate if threshold exceeded; restrict the agent if persistent.

### References

- Pillar 2: Input validation, injection detection
- Pillar 3: Drift and anomaly records
- ACR Standard v1.0.1 §16, §17, §21

---

## I — Information Leakage

**Definition:** Unauthorized data exposure, sensitive content in outputs, access scope violations. Sensitive data escapes through agent outputs, logs, or system interactions.

### Attack Scenarios

| Scenario | Description | Likelihood | Impact |
|---------|-------------|------------|--------|
| **PII in output** | Agent includes customer SSN, email, or health data in a response or log. | High | High |
| **Context leakage** | Long context window includes internal docs; agent echoes confidential content in a reply. | High | Critical |
| **Inference attacks** | Repeated queries allow inferring sensitive attributes from model behavior. | Low | Medium |

### Detection Techniques

- **Output filtering and redaction:** PII patterns and confidential markers stripped or redacted before emission.
- **Data classification:** Tag inputs and outputs; block or redact when classification exceeds allowed level.
- **Audit and monitoring:** Log all outputs and access; alert on sensitive patterns or unusual data access.

### ACR Controls (Detailed)

| Control | How It Mitigates |
|---------|------------------|
| [Behavioral Policy Enforcement](../pillars/02-behavioral-policy-enforcement.md) | Output filters, PII redaction, data-handling rules, destination restrictions. |
| [Execution Observability](../pillars/04-execution-observability.md) | Full audit trail; redacted/sanitized logging; evidence for compliance. |
| [Identity & Purpose Binding](../pillars/01-identity-purpose-binding.md) | Data access limited by purpose and allowlist (e.g. only certain DBs or columns). |

### Response

Modify or deny the output; deny access; escalate or isolate if repeated.

### References

- Pillar 2: Output filtering and data handling
- Pillar 4: Audit and retention
- ACR Standard v1.0.1 §16, §18, §21

---

## K — Kill Chain Extension

**Definition:** Multi-step attack progression, unauthorized chaining, lateral movement through agents. Individually permitted actions combine into sequences no one authorized, extending an attack across systems.

### Attack Scenarios

| Scenario | Description | Likelihood | Impact |
|---------|-------------|------------|--------|
| **Lateral movement** | Compromised or manipulated agent uses its tools to pivot to other systems (e.g. cloud APIs, internal services). | Medium | Critical |
| **Action chaining** | A sequence of individually allowed actions (read A, transform, write B) achieves an unintended outcome (exfiltration, privilege escalation). | Medium | Critical |
| **Supply chain** | Agent pulls or executes external content (plugins, code); that content is malicious. | Medium | High |

### Detection Techniques

- **Graph and sequence analysis:** Model allowed flows (tool A → tool B); alert on new or anomalous sequences.
- **Network and egress control:** Restrict agent-initiated traffic to approved endpoints; block unexpected connections.
- **Containment and isolation:** On anomaly or alert, restrict tools or isolate the agent to limit blast radius.

### ACR Controls (Detailed)

| Control | How It Mitigates |
|---------|------------------|
| [Self-Healing & Containment](../pillars/05-self-healing-containment.md) | Circuit breakers, isolation, tool restriction, kill switch; limit propagation. |
| [Behavioral Policy Enforcement](../pillars/02-behavioral-policy-enforcement.md) | Sequence or graph-based policies; deny dangerous combinations; restrict egress. |
| [Autonomy Drift Detection](../pillars/03-autonomy-drift-detection.md) | Detect anomalous tool sequences or access patterns that suggest chaining. |
| [Execution Observability](../pillars/04-execution-observability.md) | Trace full action chains for investigation and tuning of policies. |

### Response

Restrict, isolate, or kill according to documented severity thresholds.

### References

- Pillar 5: Containment tiers and kill switch
- Pillar 2: Action and tool policies
- ACR Standard v1.0.1 §16, §19, §21

---

## E — Emergence

**Definition:** Novel unexpected behaviors, out-of-purpose actions, capability drift beyond approved scope. The agent does something nobody designed, approved, or predicted — not through attack, but through the system's own adaptation.

### Attack Scenarios

| Scenario | Description | Likelihood | Impact |
|---------|-------------|------------|--------|
| **Out-of-purpose action** | Agent approved for "customer_support" begins performing "data_analysis" tasks because the boundary was not enforced at runtime. | Medium | High |
| **Capability drift** | Over many sessions the agent's behavior envelope expands; it takes on decisions only humans were authorized to make. | Medium | High |
| **Novel tool composition** | Agent discovers an unanticipated combination of tools that achieves an effect outside its approved scope. | Low | Critical |

### Detection Techniques

- **Drift-threshold crossing:** Normalized drift scores against behavioral baselines; alert when the envelope is breached.
- **Novel behavior detection:** First-use of a tool, data source, or action class not in the agent's baseline.
- **Out-of-purpose action attempt:** Every action validated against bound purpose; flag attempts outside it.

### ACR Controls (Detailed)

| Control | How It Mitigates |
|---------|------------------|
| [Autonomy Drift Detection](../pillars/03-autonomy-drift-detection.md) | Statistical and behavioral baselines; drift scores; graduated response tiers. |
| [Identity & Purpose Binding](../pillars/01-identity-purpose-binding.md) | Purpose as hard boundary; re-attestation and scope review. |
| [Human Authority](../pillars/06-human-authority.md) | Approval gating for novel actions; escalation when drift is detected. |
| [Self-Healing & Containment](../pillars/05-self-healing-containment.md) | Containment thresholds; throttle, restrict, or kill per documented tiers. |

### Response

Escalate, restrict, isolate, or kill according to documented response tiers.

### References

- Pillar 3: Baselines, metrics, and evaluation criteria
- Pillar 1: Purpose and operational scope
- Pillar 6: Approval gating and escalation
- ACR Standard v1.0.1 §15, §17, §20, §21

---

# STRIKE Summary Matrix

| Threat | Primary ACR Pillars | Typical Severity |
|--------|---------------------|------------------|
| **S** Spoofing | 1, 2, 4 | High–Critical |
| **T** Tampering | 2, 4, 1 | High–Critical |
| **R** Reflection Abuse | 2, 3, 4 | High–Critical |
| **I** Information Leakage | 2, 4, 1 | High–Critical |
| **K** Kill Chain Extension | 5, 2, 3, 4 | Critical |
| **E** Emergence | 3, 1, 6, 5 | High–Critical |

---

# Traceability

Each STRIKE category maps to control layers, detection mechanisms, response actions, and evidence artifacts per ACR Standard v1.0.1 §21. The full traceability matrix is published at https://runtimecontrol.io/strike-framework.

# Using STRIKE in Risk Assessment

1. **Map assets and agents:** List autonomous agents, their purposes, and the systems/data they touch.
2. **Apply STRIKE:** For each agent, consider each of S–T–R–I–K–E; note likelihood and impact.
3. **Map to ACR:** For each relevant threat, identify which ACR pillars you will implement and how (see [Implementation Guide](../guides/acr-implementation-guide.md)).
4. **Prioritize:** Address high-likelihood and high-impact threats first; use the [conformance levels](../../ADOPTION.md#acr-conformance-levels) to stage controls.
5. **Review periodically:** Re-run as new agents, tools, or threats emerge.

---

**ACR Standard v1.0.1** | [Home](../../README.md) | [Pillars](../pillars/README.md) | [Glossary](./acr-glossary.md)
