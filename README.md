# ACR Framework
## Autonomous Control & Resilience for Runtime AI Governance

**An open reference architecture for governing autonomous AI systems in production environments.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0-green.svg)](https://github.com/SynergeiaLabs/acr-framework/releases)
[![Framework](https://img.shields.io/badge/type-reference%20architecture-orange.svg)]()

📖 [Read the Docs](./docs) | 🎯 [Use Cases](./docs/guides/acr-use-cases.md) | 🔒 [Threat Model](./docs/security/acr-strike-threat-model.md) | 🗺️ [NIST Mapping](./docs/compliance/acr-nist-ai-rmf-mapping.md) | 📋 [Adopt ACR](./ADOPTION.md)

---

## Overview

The **ACR Framework** defines a runtime governance architecture for autonomous AI systems operating in enterprise production environments.

As AI systems evolve from static models into autonomous agents—capable of accessing data, invoking tools, and making operational decisions—traditional governance approaches centered on policy documentation and pre-deployment reviews no longer provide sufficient control.

**ACR establishes architectural patterns for enforcing governance during live system operation**, enabling organizations to maintain control over AI behavior in production.

---

## The Governance Gap

Traditional AI governance programs focus on design-time controls:

- **Policy frameworks:** NIST AI RMF, ISO/IEC 42001, organizational AI policies
- **Pre-deployment reviews:** Model validation, impact assessments, approval workflows  
- **Risk classification:** High/medium/low risk categorization, use case evaluation

**These controls stop at deployment.**

Once an AI system enters production, most organizations lack architectural mechanisms to:

- **Enforce behavioral constraints** during inference operations
- **Detect drift** when system behavior deviates from design intent
- **Respond automatically** to policy violations or anomalous actions
- **Maintain audit trails** with decision-level visibility
- **Intervene in real-time** when high-risk actions are attempted

This gap creates operational risk as autonomous systems interact with enterprise infrastructure, access sensitive data, and influence business processes.

**ACR addresses this gap by defining runtime control patterns adapted from proven infrastructure governance architectures.**

---

## Why ACR?

Like **OWASP** for application security and **MITRE ATT&CK** for threat modeling, ACR provides a **shared vocabulary and reference architecture** for runtime AI governance. It is:

- **Framework-agnostic** — Works with any model provider, stack, or policy engine
- **Standards-aligned** — Maps to NIST AI RMF, ISO/IEC 42001, SOC 2
- **Implementation-flexible** — API gateway, SDK, sidecar, or control-plane service patterns
- **Adoption-ready** — Maturity levels, adoption guide, citation and badge for implementers ([ADOPTION.md](./ADOPTION.md))

Whether you are building in-house controls, evaluating vendors, or preparing for audits, ACR gives you a consistent way to design, implement, and assess runtime governance.

---

## Framework Principles

ACR is built on three foundational principles:

### 1. Governance Must Execute at Runtime
Policy compliance cannot be verified only at design time. Controls must operate during system execution, enforcing boundaries as the AI system processes requests, accesses resources, and generates outputs.

### 2. Defense in Depth Through Layered Controls  
No single control mechanism is sufficient. ACR defines six complementary control layers that work together to detect, prevent, and respond to governance violations.

### 3. Adaptation of Proven Patterns to AI Context
ACR does not invent runtime governance—it adapts established infrastructure control patterns (observability, policy enforcement, circuit breakers, least privilege) to the unique characteristics of non-deterministic AI systems.

---

## ACR Architecture

ACR defines a **control plane** that mediates between autonomous AI systems and enterprise resources:

```
┌─────────────────────────────────────────────────────────────┐
│                    Enterprise Applications                   │
│              (CRM, ERP, Data Warehouses, APIs)              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   AI Systems / Agents                        │
│         (LLMs, Autonomous Agents, AI Workflows)             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  ACR RUNTIME CONTROL PLANE                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          Identity & Purpose Binding Layer              │ │
│  │   (Service identity, operational scope, capability     │ │
│  │    authorization, resource access control)             │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │        Behavioral Policy Enforcement Layer             │ │
│  │   (Input validation, output filtering, action          │ │
│  │    authorization, data handling rules)                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Autonomy Drift Detection Layer                 │ │
│  │   (Behavioral baselines, statistical monitoring,       │ │
│  │    anomaly detection, deviation alerts)                │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Execution Observability Layer                │ │
│  │   (Structured telemetry, audit trails, decision        │ │
│  │    lineage, compliance evidence)                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Self-Healing & Containment Layer               │ │
│  │   (Automated response, capability restriction,         │ │
│  │    circuit breakers, escalation triggers)              │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Human Authority Layer                     │ │
│  │   (Manual intervention, approval workflows,            │ │
│  │    override mechanisms, kill switches)                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Enterprise Systems & Data                       │
│     (Databases, File Systems, External APIs, Tools)         │
└─────────────────────────────────────────────────────────────┘
```

**The control plane enforces governance policy at runtime through six complementary control layers.**

See [ACR Control Plane Architecture](./docs/architecture/acr-control-plane-architecture.md) for detailed design.

---

## Control Layer Overview

### Layer 1: Identity & Purpose Binding

Every AI system operates with a cryptographically-bound identity tied to specific business purposes and authorized resources. Prevents operational scope expansion without approval.

**[Full Specification →](./docs/pillars/01-identity-purpose-binding.md)**

---

### Layer 2: Behavioral Policy Enforcement

Governance policies translate into machine-enforceable runtime rules for input validation, output filtering, action authorization, and data handling.

**[Full Specification →](./docs/pillars/02-behavioral-policy-enforcement.md)**

---

### Layer 3: Autonomy Drift Detection

Establishes behavioral baselines and monitors for statistical deviations indicating the system is operating outside intended parameters.

**[Full Specification →](./docs/pillars/03-autonomy-drift-detection.md)**

---

### Layer 4: Execution Observability

Captures structured telemetry for all AI operations, enabling audit trails, decision reconstruction, and compliance evidence generation.

**[Full Specification →](./docs/pillars/04-execution-observability.md)**

---

### Layer 5: Self-Healing & Containment

Enables automated response to policy violations and drift through capability restriction, workflow interruption, system isolation, and escalation.

**[Full Specification →](./docs/pillars/05-self-healing-containment.md)**

---

### Layer 6: Human Authority

Preserves human oversight through intervention mechanisms, approval workflows, override capabilities, and defined escalation paths.

**[Full Specification →](./docs/pillars/06-human-authority.md)**

---

## Implementation Approaches

ACR is an **architectural framework**, not a prescriptive implementation. Organizations can implement ACR controls using multiple approaches:

### Deployment Patterns

**API Gateway Pattern**
- Deploy control plane as reverse proxy (Envoy, Kong, NGINX)
- Intercept all model API traffic
- Centralized enforcement, language-agnostic
- Trade-off: Network hop adds latency, single point of failure

**SDK/Library Pattern**  
- Embed control logic in application code
- Wrap model API clients with governance layer
- Low latency, distributed failure domain
- Trade-off: Requires per-language SDK, version management

**Sidecar Pattern**
- Deploy control plane as sidecar container
- Intercept traffic at network layer (service mesh)
- Infrastructure-enforced, platform-native
- Trade-off: Kubernetes/mesh dependency, complexity

**Control Plane Service Pattern**
- Separate governance service layer
- Applications call control plane for policy decisions
- Centralized logic, flexible integration
- Trade-off: Additional network calls, latency sensitive

Organizations select patterns based on infrastructure, latency requirements, and operational constraints.

See [Implementation Guide](./docs/guides/acr-implementation-guide.md) for detailed deployment architectures.

---

## Standards & Compliance Alignment

ACR complements established AI governance and security frameworks:

### NIST AI Risk Management Framework (AI RMF)
- **GOVERN:** Organizational structures, policies → *ACR enforcement mechanisms*
- **MAP:** Risk identification, context → *Identity binding, threat modeling*
- **MEASURE:** Metrics, monitoring → *Observability, drift detection*
- **MANAGE:** Risk response, mitigation → *Policy enforcement, containment*

### ISO/IEC 42001 (AI Management Systems)
- **Clause 6.1 (Risk Management):** Risk assessment → *Drift detection, threat model*
- **Clause 8.2 (Operation):** Operational controls → *Policy enforcement, observability*
- **Clause 9.1 (Monitoring):** Performance monitoring → *Telemetry, metrics*
- **Clause 10.1 (Nonconformity):** Corrective action → *Containment, incident response*

### SOC 2 Type II Controls
- **CC6.1 (Logical Access):** Access controls → *Identity binding, RBAC*
- **CC7.2 (System Monitoring):** Monitoring controls → *Observability, alerting*
- **CC8.1 (Change Management):** Change controls → *Drift detection, baselines*
- **PI1.4 (Privacy):** Data privacy → *Output filtering, PII redaction*

See [NIST AI RMF Mapping](./docs/compliance/acr-nist-ai-rmf-mapping.md) for detailed control mappings.

---

## Use Cases

ACR applies to autonomous AI systems across enterprise contexts:

- **Customer Service Agents:** Enforce data privacy, prevent unauthorized discounts, detect tone drift
- **Data Analysis Agents:** Control database access, prevent SQL injection, monitor query patterns
- **Code Generation Agents:** Restrict file system access, block credential exposure, detect malicious code patterns
- **Document Processing Agents:** Enforce PII handling, control external API calls, monitor extraction accuracy
- **Multi-Agent Workflows:** Coordinate inter-agent authorization, maintain workflow audit trails, contain cascading failures

See [ACR Use Cases](./docs/guides/acr-use-cases.md) for detailed scenarios and control applications.

---

## Documentation

### Core Framework
- **[Framework README](./README.md)** - This document
- **[Control Plane Architecture](./docs/architecture/acr-control-plane-architecture.md)** - Technical architecture
- **[Runtime Architecture](./docs/architecture/acr-runtime-architecture.md)** - Deployment patterns
- **[Production Lifecycle](./docs/architecture/acr-production-lifecycle.md)** - End-to-end workflow

### Pillar Specifications
- **[Pillars Overview](./docs/pillars/README.md)** - All six control layers
- **[Layer 1: Identity & Purpose Binding](./docs/pillars/01-identity-purpose-binding.md)**
- **[Layer 2: Behavioral Policy Enforcement](./docs/pillars/02-behavioral-policy-enforcement.md)**
- **[Layer 3: Autonomy Drift Detection](./docs/pillars/03-autonomy-drift-detection.md)**
- **[Layer 4: Execution Observability](./docs/pillars/04-execution-observability.md)**
- **[Layer 5: Self-Healing & Containment](./docs/pillars/05-self-healing-containment.md)**
- **[Layer 6: Human Authority](./docs/pillars/06-human-authority.md)**

### Technical Specifications
- **[Telemetry Schema](./docs/specifications/telemetry-schema.md)** - JSON schema for observability
- *Policy DSL Requirements* (planned v1.1)
- *Drift Detection Requirements* (planned v1.1)

### Security & Compliance
- **[STRIKE Threat Model](./docs/security/acr-strike-threat-model.md)** - AI-specific threats
- **[NIST AI RMF Mapping](./docs/compliance/acr-nist-ai-rmf-mapping.md)** - Compliance alignment
- **[Glossary](./docs/security/acr-glossary.md)** - Term definitions

### Getting Started
- **[FAQ](./docs/guides/FAQ.md)** - Frequently asked questions
- **[Implementation Guide](./docs/guides/acr-implementation-guide.md)** - Deployment guidance
- **[Use Cases](./docs/guides/acr-use-cases.md)** - Real-world scenarios

---

## Contributing

ACR is an open framework designed to evolve with the autonomous AI ecosystem.

**Contribution areas:**
- Control layer refinements and extensions
- Implementation pattern documentation
- Threat model expansion (new attack vectors, mitigations)
- Standards mappings (EU AI Act, sector-specific regulations)
- Case studies and deployment experiences
- Research on drift detection, policy languages, observability schemas

**Contribution process:**
1. Review existing issues and discussions
2. Open issue describing proposed contribution
3. Discuss approach and alignment with ACR principles
4. Submit pull request with documentation updates
5. Community review and merge

**Code contributions:**
ACR is an architectural framework—reference implementations are welcome but maintained separately. The core framework repository focuses on specifications, design patterns, and architectural guidance.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines.

---

## Framework Governance

**Maintainer:** Adam DiStefano ([@SynergeiaLabs](https://github.com/SynergeiaLabs))

**Roadmap:**
- **v1.0 (Current):** Core six-layer architecture, NIST/ISO mappings, threat model
- **v1.1 (Q2 2026):** Expanded implementation patterns, telemetry schema standardization
- **v1.2 (Q3 2026):** Multi-model orchestration patterns, federated governance
- **v2.0 (2027):** Extensions for emerging AI architectures, regulatory compliance modules

See [ROADMAP.md](./ROADMAP.md) for detailed development plan. For project structure, decision-making, and working groups, see [GOVERNANCE.md](./GOVERNANCE.md).

**Community:**
- GitHub Discussions: Architecture questions, use case sharing
- Monthly community calls: Framework evolution, implementation experiences (planned Q2 2026)
- Working groups: Drift detection, policy languages, observability standards

---

## Implementations

Organizations and vendors implementing ACR-aligned solutions are listed below. To **add your implementation**, see [ADOPTION.md](./ADOPTION.md) (criteria, maturity levels, and how to submit a listing).

**Open Source:**
- [ACR Control Plane](./implementations/acr-control-plane) — reference control-plane implementation for runtime governance ([upstream](https://github.com/SynergeiaLabs/proofstream-mvp)).
- *[Add community implementations as they emerge]*

**Commercial:**
- *[Products implementing ACR patterns can self-register here]*

**Research:**
- *[Academic implementations and extensions]*

**Note:** ACR is a framework specification. Listing does not imply endorsement; implementations self-declare alignment. Maturity levels (1–3) are defined in [ADOPTION.md](./ADOPTION.md).

---

## License

Apache 2.0 License - see [LICENSE](./LICENSE)

This framework is freely available for use, modification, and distribution. Commercial implementations are encouraged.

---

## Citation and Branding

If you reference ACR in research, standards, or product documentation, please cite:

```bibtex
@misc{acr-framework-2026,
  author = {DiStefano, Adam},
  title = {ACR Framework: Autonomous Control \& Resilience for Runtime AI Governance},
  year = {2026},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/SynergeiaLabs/acr-framework}},
  version = {1.0}
}
```

Implementers may use the **ACR Aligned** badge and refer to [ADOPTION.md](./ADOPTION.md) for citation text, logo usage, and maturity levels.

---

## Resources

- **Website:** [autonomouscontrol.io](https://autonomouscontrol.io)
- **Documentation:** [docs](./docs)
- **Adoption & maturity:** [ADOPTION.md](./ADOPTION.md)
- **Governance:** [GOVERNANCE.md](./GOVERNANCE.md)
- **Contributing:** [CONTRIBUTING.md](./CONTRIBUTING.md)
- **Discussions:** [GitHub Discussions](https://github.com/SynergeiaLabs/acr-framework/discussions)
- **Issues:** [GitHub Issues](https://github.com/SynergeiaLabs/acr-framework/issues)

---

**ACR Framework v1.0** | March 2026 | Runtime Governance for Autonomous AI | [Cite](README.md#citation-and-branding) | [Adopt](ADOPTION.md)
