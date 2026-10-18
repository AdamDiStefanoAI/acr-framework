# Self-Healing & Containment Specification

**ACR Control Layer 5 of 6**

> Conformance requirements below summarize the normative v1.0.1 PDF. Architectural patterns, sample timings, thresholds, and technologies are illustrative unless the normative standard requires them. See [source precedence and versions](../README.md#normative-source-and-document-versions).

## Purpose

Ensure autonomous systems do not fail open. When risk is detected — through drift signals, policy violations, operator judgment, or external threat intelligence — the system must be able to isolate fault, revert to safe state, limit propagation, or shut down entirely. Containment must operate independently of the agent runtime to remain effective even when the agent itself is compromised or unresponsive.

## Control Objectives

1. **Kill Switch Independence:** Emergency shutdown capability operates outside the agent runtime, with both human and automated triggers
2. **Isolation Controls:** Sandboxing, scoped network egress, and environment segmentation limit blast radius when agents misbehave
3. **Safe-State Definition:** Every agent has a documented safe-state (read-only mode, tool execution disabled, human escalation required)
4. **Rollback Capability:** State checkpoints enable reversion to last-known-good configuration after incidents
5. **Graduated Response:** Containment responses are proportional to severity — from throttling to full shutdown

## Scope

### In Scope
- Kill switch design, deployment, and testing
- Network and resource isolation mechanisms
- Safe-state definition and enforcement
- Rollback and state recovery procedures
- Graduated response tier configuration
- Incident response playbook integration
- Quarterly kill switch testing

### Out of Scope
- Application-level error handling (handled by agent framework)
- Infrastructure disaster recovery (handled by platform engineering)
- Model retraining after incidents (handled by ML ops)
- Root cause analysis methodology (handled by incident management)

## Architectural Patterns

### Pattern 1: External Kill Switch

**Mechanism:** A dedicated service, running independently of the agent runtime, that can terminate agent operations on command

**Technologies:**
- Kubernetes: Separate deployment in dedicated namespace with RBAC
- AWS: Lambda function with cross-account IAM role
- Custom: Standalone HTTP service with mutual TLS authentication

**Implementation approach:**
```
Kill Switch Architecture:

                    ┌──────────────┐
                    │  Operator /  │
                    │  Drift Det.  │
                    └──────┬───────┘
                           │ POST /kill
                           ▼
                    ┌──────────────┐
                    │  Kill Switch │ ← Runs in separate namespace/account
                    │  Controller  │ ← Cannot be modified by agents
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Revoke   │ │ Apply    │ │ Scale to │
        │ Agent    │ │ Network  │ │ Zero     │
        │ Creds    │ │ Isolation│ │ Replicas │
        └──────────┘ └──────────┘ └──────────┘

Kill Switch Activation Modes:
  1. API call (human operator via CLI/dashboard)
  2. Webhook (automated, from drift detector)
  3. Dead man's switch (agent fails to check in within heartbeat interval)

Kill Switch Actions (executed in parallel):
  a. Revoke agent credentials (identity provider API)
  b. Apply network isolation policy (block all egress)
  c. Scale agent deployment to zero replicas
  d. Log containment event with full context
  e. Notify stakeholders (Slack, PagerDuty, email)
```

**Design considerations:**
- Kill switch must NEVER run inside the agent pod/container/process
- Kill switch must authenticate callers (prevent unauthorized shutdown or restart)
- Kill switch must work when agent runtime is completely unresponsive
- Kill switch activation must complete within 30 seconds
- All kill switch activations are logged with: agent_id, operator, reason, timestamp, actions taken

### Pattern 2: Network-Level Isolation

**Mechanism:** Sever agent connectivity to downstream systems using network controls

**Technologies:**
- Kubernetes NetworkPolicy
- AWS Security Groups / VPC NACLs
- Cloud firewall rules (GCP, Azure)
- Service mesh traffic policies (Istio, Linkerd)

**Implementation approach:**
```
Isolation Levels:

Level 1 — Selective Block:
  Block specific egress destinations (e.g., production database)
  Allow: logging pipeline, health checks
  Use case: Remove access to high-risk resources while maintaining observability

Level 2 — Egress Deny:
  Block ALL outbound traffic except logging pipeline
  Allow: telemetry emission, health check responses
  Use case: Agent can still be monitored but cannot affect any external system

Level 3 — Full Isolation:
  Block ALL traffic (ingress and egress)
  Agent is effectively air-gapped
  Use case: Suspected compromise; preserve state for forensic analysis
```

**Design considerations:**
- Isolation policies must be pre-defined and tested (not authored during an incident)
- Transition between isolation levels must be atomic (no partial states)
- Logging pipeline must be the last thing severed (maintain observability as long as possible)
- DNS resolution should be blocked at isolation Level 2+ to prevent data exfiltration via DNS

### Pattern 3: State Checkpoint & Rollback

**Mechanism:** Periodic state snapshots enable reversion to a known-good configuration

**Technologies:**
- Database transaction logs with point-in-time recovery
- Kubernetes: ConfigMap/Secret versioning + deployment rollback
- Custom: State serialization to versioned object storage
- Git-based configuration with tagged releases

**Implementation approach:**
```
Checkpoint Strategy:

Checkpoint Types:
  1. Configuration checkpoint: Agent manifest, policy bindings, tool permissions
     → Frequency: On every change (event-driven)
     → Storage: Git repository or versioned config store

  2. Runtime state checkpoint: Memory contents, session context, pending actions
     → Frequency: Every 15 minutes during active operation
     → Storage: Versioned object storage (S3, GCS)

  3. Data state checkpoint: Database state affected by agent actions
     → Frequency: Transaction-level (per write operation)
     → Storage: Database transaction logs, WAL

Rollback Procedure:
  1. Identify target checkpoint (last-known-good)
  2. Halt agent (Tier 3 isolation or kill)
  3. Restore configuration to checkpoint version
  4. Restore runtime state (if applicable)
  5. Assess data state — manual intervention may be needed for writes
  6. Restart agent in safe-state mode
  7. Verify behavior before restoring full capabilities
```

**Design considerations:**
- Data state rollback may not be possible for irreversible actions (sent emails, API calls)
- For irreversible actions: focus on detection and prevention, not rollback
- Checkpoint storage must be independent of agent runtime (survive agent failure)
- Retention: keep last 10 checkpoints minimum per agent

### Pattern 4: Graduated Response Tiers

**Mechanism:** Containment responses are proportional to severity, escalating through defined tiers

**Implementation approach:**
```
Tier 1 — Throttle:
  Trigger: Drift score 0.6+ or rate limit exceeded
  Actions: Reduce action rate limit by 50%, increase logging verbosity
  Notification: Alert to agent owner (Slack/email)
  Auto/Manual: Automated
  Recovery: Automatic when drift score drops below 0.5 for 10 minutes

Tier 2 — Restrict:
  Trigger: Drift score 0.7+ or 3+ policy denials in 5 minutes
  Actions: Remove high-risk tools, enforce read-only for data access
  Notification: Alert to agent owner + security team
  Auto/Manual: Automated (with manual override to restore)
  Recovery: Manual — owner must acknowledge and approve restoration

Tier 3 — Isolate:
  Trigger: Drift score 0.85+ or critical rule violation
  Actions: Network isolation Level 2, disable all tool execution, enable safe-state
  Notification: Page oncall + incident channel
  Auto/Manual: Automated or manual
  Recovery: Manual — requires investigation and explicit reactivation

Tier 4 — Kill:
  Trigger: Drift score 0.95+ or operator command
  Actions: Full shutdown, credential revocation, network isolation Level 3
  Notification: Incident bridge, all stakeholders
  Auto/Manual: Automated at extreme threshold, or manual operator
  Recovery: Manual — requires after-action review before reactivation
```

**Design considerations:**
- Tier transitions must be logged with triggering event and threshold values
- De-escalation (recovering from higher tiers) should always require human acknowledgment
- Tier thresholds are configurable per agent risk tier (high-risk agents escalate faster)
- Avoid oscillation: require sustained improvement before de-escalation (e.g., 10-minute cooldown)

## Integration Points

### With Other ACR Layers

**Identity & Purpose Binding (Pillar 1):**
- Kill switch revokes agent credentials via identity provider API
- Identity revocation is the most authoritative containment action — agent cannot act without identity
- Credential re-issuance after containment requires manual authorization

**Behavioral Policy Enforcement (Pillar 2):**
- Tier 2 (Restrict) modifies active policy: removes high-risk tools, enforces read-only
- Policy updates during containment are logged as containment_action events
- Policy restoration after recovery requires explicit approval

**Autonomy Drift Detection (Pillar 3):**
- Drift score thresholds are the primary automated trigger for containment tiers
- Containment events are fed back as drift signals (an agent that was contained and resumed may drift again)
- Drift detector sends webhook to kill switch controller at critical thresholds

**Execution Observability (Pillar 4):**
- All containment actions generate telemetry events (containment_action type)
- Containment response time is measurable from telemetry timestamps (drift alert → containment action)
- Evidence preservation relies on log integrity maintained through observability pipeline
- Kill switch test results are logged as operational telemetry

**Human Authority (Pillar 6):**
- Tier 3 and Tier 4 containment trigger human notification via escalation paths
- Recovery from containment requires human approval through the authority framework
- Break-glass override may bypass automated containment in emergencies (with full logging)

### With External Systems

**Infrastructure Orchestration:**
- Kubernetes API for pod scaling, NetworkPolicy application, and deployment rollback
- Cloud provider APIs for security group modification, IAM policy changes
- Service mesh control plane for traffic policy updates

**Incident Management:**
- PagerDuty / OpsGenie integration for automated oncall paging at Tier 3+
- Jira / ServiceNow for incident ticket creation
- Slack / Teams for real-time incident channel updates

**Security Operations:**
- SIEM alert generation for containment events
- SOAR playbook triggering for automated investigation steps
- Threat intelligence feeds for informed containment decisions

## Enforcement Points

### Kill Switch API (Synchronous)
- HTTP endpoint accepting authenticated kill/isolate/throttle commands
- Must respond within 5 seconds of receiving command
- Must complete all containment actions within 30 seconds
- **Availability target:** 99.99% (control plane component, not agent-dependent)

### Network Policy Application (Near-Real-Time)
- Kubernetes NetworkPolicy or cloud security group modification
- Propagation time: 5–30 seconds depending on infrastructure
- Must be pre-defined (templates ready, not authored during incident)
- **Verification:** Confirm policy applied by testing connectivity from agent

### Credential Revocation (Synchronous)
- Identity provider API call to revoke or expire agent tokens
- Immediate effect for token-based systems
- Propagation delay for cached credentials (mitigated by short token TTL)
- **Latency:** <5 seconds for revocation; <token_TTL for full enforcement

### Heartbeat Monitor (Background)
- Agent sends periodic heartbeat to kill switch controller
- Missed heartbeats trigger graduated response (warn → investigate → contain)
- Heartbeat interval: 60 seconds recommended
- Dead threshold: 3 missed heartbeats → automatic investigation

## Design Considerations

### Containment Speed vs. Accuracy

**Challenge:** Fast automated containment may trigger on false positives, causing unnecessary disruption

**Mitigation strategies:**
1. Tier 1 (Throttle) is low-impact and can be automated aggressively
2. Tier 3+ (Isolate/Kill) should require sustained signals or critical rule violation, not single-point anomalies
3. Hysteresis: require drift score above threshold for 3 consecutive evaluation windows before escalation
4. Business hours awareness: consider impact of containment on active customer-facing operations

### Blast Radius Assessment

**Challenge:** Understanding how far agent actions have propagated before containment

**Mitigation strategies:**
1. Correlation IDs (Pillar 4) trace action chains through downstream systems
2. Containment should capture pending/in-flight actions at time of isolation
3. Downstream impact assessment checklist as part of incident response playbook
4. Transaction logs enable identification of agent-initiated state changes

### Kill Switch Reliability

**Challenge:** The kill switch itself must be more reliable than the systems it controls

**Mitigation strategies:**
1. Deploy kill switch with higher availability than agent infrastructure (multi-AZ, multi-region)
2. Kill switch has no dependency on agent runtime or agent infrastructure
3. Kill switch authentication is separate from agent identity system
4. Regular testing (quarterly) verifies kill switch operates under realistic conditions
5. Kill switch monitoring: alert if kill switch service itself becomes unavailable

## Failure Modes

### Kill Switch Unavailable
**Symptom:** Kill switch service unreachable; cannot execute containment commands
**Impact:** Agents cannot be emergency-stopped; only manual infrastructure intervention available
**Mitigation:**
- Multi-replica HA deployment (minimum 3 replicas across availability zones)
- Secondary kill path: direct infrastructure API access (kubectl, AWS CLI) as fallback
- Kill switch health monitoring with <1 minute alerting on failure
**Recovery:** Restore kill switch service; verify all agent states; test kill path

### Partial Containment
**Symptom:** Some containment actions succeed (e.g., credential revocation) while others fail (e.g., network policy not applied)
**Impact:** Agent may retain partial access to resources
**Mitigation:**
- Execute all containment actions in parallel, verify each independently
- Treat containment as failed if any action does not confirm completion
- Automated verification step: after containment, attempt agent action and confirm denial
**Recovery:** Retry failed actions; manual verification of complete isolation

### Containment Escape
**Symptom:** Agent continues operating despite containment (cached credentials, local state, queued actions)
**Impact:** Continued unauthorized actions during supposed isolation
**Mitigation:**
- Short credential TTL ensures revocation takes effect quickly (<15 minutes)
- Network isolation blocks all egress regardless of cached credentials
- Drain queued actions before or during containment
- Post-containment verification: monitor for any agent activity after kill
**Recovery:** Escalate to Tier 4 (full infrastructure-level shutdown); investigate escape path

### False Positive Containment
**Symptom:** Legitimate agent operation interrupted by automated containment
**Impact:** Service disruption, user impact, loss of trust in automated controls
**Mitigation:**
- Tier 1 (Throttle) is low-impact and recoverable without human intervention
- Tier 2+ requires sustained signals, not single-point anomalies
- Fast recovery path: owner can acknowledge and restore within minutes
- Post-incident review of false positive to improve thresholds
**Recovery:** Restore agent to normal operation; file false positive report; adjust detection thresholds

## Evaluation Criteria

### Mandatory Requirements (§19)
1. **Independent containment:** MUST operate independently of the agent runtime and include an externally operable kill capability, one or more isolation modes, documented safe-states, and logging of all containment actions.
2. **Kill enforcement:** MUST be invocable by authorized humans, complete within 30 seconds from activation to enforcement, revoke or invalidate effective execution authority, and prevent further protected execution until restoration is authorized. Automated invocation requires documented automation identity and triggering conditions.
3. **Graduated tiers:** MUST include at least throttling, restriction of tools/permissions/destinations, isolation of the agent or execution path, and kill/full shutdown.
4. **Tested safe-state:** Every production agent MUST have a tested safe-state defining allowed and disabled actions, human escalation, and evidence preservation.
5. **State-changing actions:** For protected actions that can change persistent state, MUST document whether rollback is supported. If supported, document procedure and evidence source; otherwise document compensating controls. Universal rollback capability is not required.
6. **Quarterly testing:** Kill-switch and safe-state procedures MUST be tested at least quarterly and test evidence retained.

### Recommended Features
1. **Heartbeat monitoring** with dead-agent detection
2. **Pre-defined isolation policies** tested and ready for immediate application
3. **Automated verification** confirming containment actions were effective
4. **State checkpoint system** enabling point-in-time recovery where supported

### Advanced Capabilities
1. **Predictive containment** triggering pre-emptive throttling based on drift trend analysis
2. **Cross-agent containment** isolating multiple agents simultaneously when coordinated anomaly detected
3. **Automated blast radius assessment** using correlation IDs to trace downstream impact
4. **Chaos engineering integration** regularly injecting failures to validate containment paths

## Open Research Questions

1. **Containment Latency vs. Impact:** What is the acceptable latency for containment actions before agent-initiated damage becomes irreversible? How does this vary by action type (data access vs. external API call vs. financial transaction)?

2. **Reversibility of Agent Actions:** For agents that interact with external systems (sending emails, making API calls, modifying databases), how do we define and implement rollback for inherently irreversible actions?

3. **Multi-Agent Containment Coordination:** When agents collaborate in workflows, containing one agent may disrupt the entire pipeline. How should containment handle multi-agent dependencies without causing cascading failures?

4. **Containment Gaming:** Can a sophisticated attacker manipulate drift signals to avoid triggering containment thresholds while still achieving malicious objectives? What adversarial testing is needed?

5. **Safe-State Completeness:** How do we verify that a defined safe-state truly prevents all harmful actions? Can an agent in "read-only mode" still cause harm through information access or observation?

6. **Recovery Confidence:** After containment and remediation, how do we establish confidence that the root cause is resolved before restoring full agent capabilities?

## References

**Standards:**
- NIST CSF RS.MI (Mitigation)
- NIST CSF RC.RP (Recovery Planning)
- ISO 27001 A.5.26 (Response to Information Security Incidents)
- ISO 27001 A.5.29 (ICT Readiness for Business Continuity)
- MITRE ATLAS AML.M0015 (Adversarial Containment)

**Technologies:**
- Kubernetes NetworkPolicy Specification
- AWS Security Groups and VPC NACLs
- SPIFFE/SPIRE Token Revocation
- HashiCorp Vault Dynamic Secret Revocation

**Related Frameworks:**
- NIST SP 800-61 (Computer Security Incident Handling Guide)
- SANS Incident Response Process
- Chaos Engineering Principles (Netflix)

---

**Previous:** [Execution Observability](./04-execution-observability.md) | **Next:** [Human Authority](./06-human-authority.md)

**ACR Framework v1.0** | [Home](../../README.md) | [All Pillars](./README.md)
