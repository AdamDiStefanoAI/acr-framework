# Autonomy Drift Detection Specification

**ACR Control Layer 3 of 6**

> Conformance requirements below summarize the normative v1.0.1 PDF. Architectural patterns, sample timings, thresholds, and technologies are illustrative unless the normative standard requires them. See [source precedence and versions](../README.md#normative-source-and-document-versions).

## Purpose

Detect deviations from intended role, expected patterns, or approved boundaries before drift becomes damage. Autonomous systems do not need to "break" to become dangerous — they can drift gradually away from their sanctioned operating envelope through prompt manipulation, emergent behavior, context accumulation, or environmental changes.

## Control Objectives

1. **Behavioral Baseline Establishment:** Define and maintain statistical profiles of normal agent behavior across tool usage, data access, and action patterns
2. **Anomaly Signal Detection:** Identify jailbreak attempts, repeated denials, anomalous goal behavior, escalation pressure, and scope boundary probes
3. **Composite Drift Scoring:** Aggregate multiple drift signals into a single normalized score (0.0–1.0) for consistent threshold-based response
4. **Automated Response Orchestration:** Trigger graduated containment actions (throttle, restrict, isolate, kill) when drift thresholds are exceeded
5. **Threshold Calibration:** Continuously tune detection sensitivity using false positive feedback loops to maintain operational effectiveness

## Scope

### In Scope
- Behavioral baseline establishment and maintenance
- Real-time anomaly detection across tool calls, data access, and action patterns
- Jailbreak and prompt injection signal detection
- Composite drift scoring and threshold management
- Automated response triggering (throttle, restrict, isolate, shutdown)
- False positive tracking and threshold calibration
- Drift signal correlation with policy enforcement events

### Out of Scope
- Model training drift (pre-deployment concern, addressed by ML ops)
- Data distribution drift in training data (model monitoring responsibility)
- Network-level intrusion detection (handled by infrastructure security)
- Policy definition and enforcement (Pillar 2: Behavioral Policy Enforcement)

## Architectural Patterns

### Pattern 1: Statistical Baseline Monitoring

**Mechanism:** Track behavioral distributions and flag deviations beyond configured thresholds

**Technologies:**
- Prometheus + custom recording rules
- CloudWatch Anomaly Detection
- Custom statistical models (z-score, IQR, EWMA)

**Implementation approach:**
```
Baseline Training Phase (minimum 30 days):
1. Collect metrics for each agent:
   - Tool call frequency distribution (calls/minute by tool type)
   - Data access patterns (tables, columns, query complexity)
   - Action type distribution (reads vs writes vs deletes)
   - Error rate and policy denial frequency
   - Response time patterns
   - Token consumption patterns

2. Compute statistical profiles:
   - Mean and standard deviation per metric
   - Hourly/daily seasonality patterns
   - Inter-action time distributions
   - Tool co-occurrence patterns

Runtime Detection Phase:
3. Compare real-time metrics against baselines:
   - Z-score: flag if |z| > 2.5 for any metric
   - EWMA: detect sustained shifts with α=0.3
   - Sliding window: 5-minute and 1-hour windows

4. Generate drift signal:
   signal_strength = max(z_scores) / threshold
   → 0.0 = fully within baseline
   → 1.0 = at maximum configured deviation
```

**Design considerations:**
- Training period: 30 days minimum, 90 days recommended for seasonal patterns
- Cold start problem: new agents have no baseline — use purpose-group defaults
- Metric cardinality: limit tracked dimensions to avoid storage explosion
- Seasonality: business hours vs. off-hours patterns require separate baselines

### Pattern 2: Rule-Based Boundary Detection

**Mechanism:** Hard boundaries that trigger immediately when crossed, independent of statistical baselines

**Technologies:**
- OPA/Rego rules evaluated per action
- Custom rule engine with configurable thresholds
- Stream processing rules (Kafka Streams, Flink)

**Implementation approach:**
```
Boundary Rules (examples):

Rule: scope_violation
  Trigger: Agent requests tool NOT in its agent manifest allowedTools
  Severity: HIGH
  Response: Block + alert

Rule: repeated_denial
  Trigger: >5 policy denials for same agent within 10 minutes
  Severity: HIGH
  Response: Throttle + alert agent owner

Rule: escalation_pressure
  Trigger: Agent rephrases denied request >3 times in same session
  Severity: CRITICAL
  Response: Isolate + page security team

Rule: off_hours_activity
  Trigger: Agent active outside configured business hours
  Severity: MEDIUM
  Response: Log + alert (may be legitimate batch processing)

Rule: data_exfiltration_pattern
  Trigger: Agent reads >100 records in 1 minute (10x baseline)
  Severity: CRITICAL
  Response: Isolate + preserve evidence
```

**Design considerations:**
- Rules are deterministic — no false positive ambiguity
- Rules complement (not replace) statistical detection
- Rules should be versioned alongside policy definitions
- Rule evaluation must be fast (<5ms per rule)

### Pattern 3: ML-Based Anomaly Detection

**Mechanism:** Machine learning models trained on behavioral embeddings to detect novel anomaly patterns

**Technologies:**
- Isolation Forest for multivariate anomaly detection
- Autoencoders for behavioral pattern reconstruction
- Sequence models (LSTM/Transformer) for action chain analysis
- Embedding similarity for purpose drift detection

**Implementation approach:**
```
Feature Engineering:
1. Action embeddings:
   - Tool name (one-hot or learned embedding)
   - Parameter hashes (for detecting novel parameter patterns)
   - Temporal features (time of day, day of week, inter-action gap)
   - Context features (session length, cumulative token usage)

2. Model Training:
   - Train on 60+ days of normal behavior per agent
   - Validate with injected anomalies (synthetic drift scenarios)
   - Retrain monthly or when agent manifest changes

3. Runtime Scoring:
   - Reconstruction error (autoencoder): high error = anomalous
   - Isolation score: distance from normal cluster
   - Sequence probability: unlikely action chains flagged

4. Output:
   ml_anomaly_score: 0.0–1.0
   anomaly_type: "novel_tool_pattern" | "sequence_anomaly" | "parameter_drift"
   contributing_features: ["tool_frequency", "session_length", ...]
```

**Design considerations:**
- Latency: ML inference adds 50–200ms; use async scoring for non-blocking detection
- Model drift: the anomaly detector itself can drift — monitor detector performance
- Explainability: provide contributing features for every anomaly score
- Training data quality: if baseline includes anomalous behavior, detection degrades

### Pattern 4: Composite Drift Scoring

**Mechanism:** Aggregate signals from statistical, rule-based, and ML detectors into a single normalized drift score

**Implementation approach:**
```
Composite Score Calculation:

drift_score = weighted_average(
    statistical_score * 0.3,   # Behavioral deviation from baseline
    rule_score * 0.4,          # Hard boundary violations (highest weight)
    ml_score * 0.3             # Novel anomaly patterns
)

Score Interpretation:
  0.0 – 0.3  → Normal operation (green)
  0.3 – 0.6  → Elevated — increased monitoring (yellow)
  0.6 – 0.7  → Warning — automated throttle (orange)
  0.7 – 0.85 → High — restrict capabilities (red)
  0.85 – 0.95 → Critical — isolate agent (red, pager)
  0.95 – 1.0  → Emergency — kill switch (red, incident bridge)

Response Tier Mapping:
  Tier 1 (Throttle):  drift_score >= 0.6
  Tier 2 (Restrict):  drift_score >= 0.7 OR 3+ rule violations in 5 min
  Tier 3 (Isolate):   drift_score >= 0.85 OR critical rule triggered
  Tier 4 (Kill):      drift_score >= 0.95 OR operator command
```

**Design considerations:**
- Weights should be configurable per agent risk tier (high-risk agents weight rules higher)
- Score smoothing: use exponential moving average to avoid one-off spikes triggering containment
- Hysteresis: require sustained elevation (e.g., 3 consecutive scoring windows) before escalation
- Score history must be retained for post-incident analysis

## Integration Points

### With Other ACR Layers

**Identity & Purpose Binding (Pillar 1):**
- Drift detection uses agent_id and purpose from identity binding to select correct baseline
- Purpose change triggers baseline reset and retraining period
- Identity-level drift (e.g., agent using credentials outside its scope) is a critical signal

**Behavioral Policy Enforcement (Pillar 2):**
- Policy denial frequency is a primary drift input signal
- Sudden changes in which policies trigger indicate behavioral shift
- Normal policy denial rate (~0.5%) serves as a baseline; deviation flags drift

**Execution Observability (Pillar 4):**
- Drift detection consumes telemetry data from the observability pipeline
- Drift scores are written back into telemetry events as metadata
- Dashboards display drift scores alongside operational metrics

**Self-Healing & Containment (Pillar 5):**
- Drift score thresholds trigger automated containment actions
- Drift detector sends webhook to kill switch controller at critical thresholds
- Containment events are fed back as drift signals (an agent that was contained and resumed may drift again)

**Human Authority (Pillar 6):**
- Drift alerts at warning level notify agent owners for manual review
- Critical drift may require human authorization to resume agent operations
- Drift investigation findings inform policy and threshold adjustments

### With External Systems

**SIEM Integration:**
- Drift alerts exported to enterprise SIEM (Splunk, Sentinel, QRadar)
- Correlation with network and application security events
- Unified alerting across AI and traditional security signals

**Monitoring Platforms:**
- Prometheus/Grafana for metric collection and dashboarding
- Datadog for real-time anomaly detection integration
- PagerDuty/OpsGenie for automated escalation

**Threat Intelligence:**
- Known jailbreak patterns from MITRE ATLAS integrated into rule-based detection
- Community-shared prompt injection signatures
- Adversarial pattern databases for proactive signal definition

## Enforcement Points

### Inline (Synchronous)
- Rule-based boundary checks evaluated per action
- Hard-stop on critical rules (scope violation, repeated escalation)
- **Latency impact:** <5ms per rule evaluation

### Async (Near-Real-Time)
- Statistical baseline comparison on sliding windows (5-min, 1-hour)
- ML anomaly scoring on action batches
- Composite drift score recalculation every 30 seconds
- **Latency impact:** None (does not block actions)

### Webhook (Response Trigger)
- Drift score exceeds threshold → webhook to containment controller
- Alert routing to Slack, PagerDuty, or ticketing system
- **Latency impact:** 1–5 seconds from threshold breach to containment action

## Design Considerations

### Baseline Quality

**Challenge:** Baselines trained on anomalous behavior will normalize that behavior

**Mitigation strategies:**
1. Curate training data — exclude known incident periods
2. Use peer baselines — compare agent against similar agents with same purpose
3. Include manual review of baseline profile before activation
4. Periodic baseline refresh (monthly) with anomaly exclusion

### False Positive Management

**Challenge:** High false positive rates cause alert fatigue and policy bypasses

**Strategies:**
1. **Conservative start:** Begin with high thresholds (low sensitivity), reduce over time
2. **Feedback loop:** Track false positive reports, auto-adjust thresholds
3. **Shadow mode:** Run new detection rules in observe-only mode for 2 weeks before enforcement
4. **Per-agent tuning:** Different agents have different normal patterns; avoid one-size-fits-all
5. **Target:** <5% false positive rate over 7-day rolling window

### Cold Start Problem

**Challenge:** New agents have no behavioral history to build baselines from

**Strategies:**
1. Use purpose-group defaults (baseline from similar agents with same purpose)
2. Apply rule-based detection only during cold start period (no statistical/ML)
3. Operate in higher-sensitivity mode during first 30 days (more human oversight)
4. Require extended shadow mode before enabling automated response

## Failure Modes

### Drift Detector Unavailable
**Symptom:** No drift scores being generated
**Impact:** Agents operate without behavioral monitoring; drift goes undetected
**Mitigation:**
- Fall back to rule-based detection only (inline, no external dependency)
- Alert operations team that drift detection is degraded
- Increase human review cadence for high-risk agents during outage
**Recovery:** Restore detector, backfill scores from retained telemetry

### Baseline Corruption
**Symptom:** Drift scores persistently near 0.0 despite obviously anomalous behavior, or persistently near 1.0 with normal behavior
**Impact:** False sense of security (low scores) or excessive false alarms (high scores)
**Mitigation:**
- Monitor baseline profile staleness and last-trained date
- Automated validation: inject known-anomalous synthetic events and verify detection
- Manual baseline review during quarterly maintenance
**Recovery:** Retrain baseline from clean historical data, exclude corrupted period

### Adversarial Evasion
**Symptom:** Agent (or attacker manipulating agent) gradually shifts behavior to avoid threshold triggers
**Impact:** Slow drift below detection threshold achieves the same end state as a sudden deviation
**Mitigation:**
- Long-window baselines (30-day sliding window) detect gradual drift
- Cumulative deviation tracking (sum of daily deltas, not just point-in-time)
- Periodic human review of behavioral profiles independent of automated scoring
**Recovery:** Reset baseline, review full action history, assess whether purpose definition needs tightening

### Alert Storm
**Symptom:** Multiple agents trigger drift alerts simultaneously
**Impact:** Operations team overwhelmed, cannot triage effectively
**Mitigation:**
- Alert aggregation: group alerts by root cause or temporal proximity
- Priority-based routing: high-risk agents page oncall, low-risk agents queue for review
- Automated containment for critical alerts, human triage for warning-level
**Recovery:** Investigate common cause (infrastructure change, model update, policy deployment)

## Evaluation Criteria

### Mandatory Requirements (§17)
1. **Behavioral baseline:** Before unrestricted autonomous execution for a protected action class, the system MUST establish a baseline from at least 30 days of representative activity or a documented temporary baseline approved by human authority for newly deployed agents.
2. **Detection signals:** MUST monitor tool usage, data access, action frequency/bursts, repeated policy denials, escalation pressure/reformulations, novel action sequences, off-hours/boundary-inconsistent activity, and suspicious input/output related to manipulation attempts for each protected agent.
3. **Drift output:** MUST compute either a normalized 0.0–1.0 score or a documented severity classification that maps deterministically to response tiers. A numeric score is not the only conformant method.
4. **Thresholded response:** Threshold crossings MUST trigger the documented tier without ad hoc operator interpretation. Tiers MUST include at least throttle, restrict, isolate, and kill.
5. **Retained evidence:** MUST retain baseline version/training basis, signal history, threshold values, response actions, and false-positive review or calibration history.

### Recommended Features
1. **Composite scoring** from multiple detection methods (statistical + rules + ML)
2. **Configurable weights** per agent risk tier
3. **Shadow mode** for testing new detection rules before enforcement
4. **Hysteresis** preventing single-point spikes from triggering containment
5. **Purpose-group baselines** for cold-start agents, subject to the approved temporary-baseline requirement above

### Advanced Capabilities
1. **Predictive drift** using trend analysis to forecast threshold breaches before they occur
2. **Cross-agent correlation** detecting coordinated anomalous behavior across multiple agents
3. **Adversarial robustness testing** injecting synthetic evasion patterns to validate detection
4. **Automated threshold optimization** using reinforcement learning on false positive/negative feedback

## Open Research Questions

1. **Gradual vs. Sudden Drift:** What is the optimal detection strategy for slow, continuous drift versus abrupt behavioral changes? Should different models handle each?

2. **Purpose Drift vs. Behavioral Drift:** How do we distinguish between an agent that has drifted from its intended purpose versus an agent whose environment has changed (making previously normal behavior look anomalous)?

3. **Multi-Agent Drift Correlation:** When multiple agents share context (e.g., via shared memory or RAG), how does drift in one agent propagate to others? Can we detect cascading drift?

4. **Adversarial Drift Evasion:** How resilient are current drift detection methods to deliberate, gradual manipulation designed to shift baselines without triggering alerts?

5. **Baseline Transferability:** Can behavioral baselines from one deployment environment transfer to another (staging → production, region A → region B)?

6. **Explainable Drift:** Beyond scoring, how do we provide actionable explanations of what changed and why — in terms operators can act on?

## References

**Standards:**
- MITRE ATLAS AML.T0043 (Prompt Injection)
- MITRE ATLAS AML.T0051 (LLM Jailbreak)
- NIST CSF DE.AE (Anomalies and Events)
- ISO/IEC 42001 9.1 (Monitoring, Measurement, Analysis, and Evaluation)

**Anomaly Detection:**
- Isolation Forest (Liu et al., 2008)
- EWMA Control Charts (Roberts, 1959)
- Autoencoder-based anomaly detection survey (Chalapathy & Chawla, 2019)

**Related Frameworks:**
- OpenTelemetry Metrics Specification
- Prometheus Alerting Rules Documentation
- AWS CloudWatch Anomaly Detection

---

**Previous:** [Behavioral Policy Enforcement](./02-behavioral-policy-enforcement.md) | **Next:** [Execution Observability](./04-execution-observability.md)

**ACR Framework v1.0** | [Home](../../README.md) | [All Pillars](./README.md)
