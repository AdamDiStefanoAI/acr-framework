# ACR Standard - Frequently Asked Questions

**Last Updated:** April 2026

## General Questions

### What is the ACR Standard?

ACR (Agentic Control at Runtime) is an open reference architecture for governing agentic AI systems at runtime. It defines six control layers that enable organizations to monitor, constrain, and intervene in AI system behavior while those systems are operating in production.

### Is ACR a product or a framework?

ACR is a standard for governing agentic AI systems at runtime. It defines the control architecture, enforcement model, and required safeguards. It is not a product, though it includes reference implementations.

### Who created ACR?

ACR was created by Adam DiStefano, AI Security & Governance Leader, based on years of experience implementing runtime governance for enterprise AI systems.

### Is ACR open source?

Yes. ACR Standard is released under the Apache 2.0 license, allowing free use, modification, and distribution.

---

## Scope & Applicability

### What types of AI systems does ACR govern?

ACR is designed for **agentic AI systems** — systems that can access data, invoke tools, make decisions, and interact with enterprise infrastructure. This includes:
- AI agents (customer service bots, data analysts, code assistants)
- Multi-agent workflows
- AI-powered automation systems
- LLM-based applications with tool access

ACR is less applicable to static models with no autonomy (e.g., image classifiers, sentiment analyzers).

### Does ACR work with all LLM providers?

Yes. ACR is provider-agnostic and works with OpenAI, Anthropic, Google, AWS, Azure, and open-source models. The framework defines interfaces and patterns, not specific API integrations.

### Can I use ACR with closed-source models?

Yes. ACR controls operate at the application layer (between your system and the model API), so it works regardless of whether the model is open or closed source.

### Does ACR only work for text-based AI?

No. While many examples use LLMs, ACR principles apply to multimodal AI (vision, speech), autonomous agents in robotics, and other AI paradigms where runtime governance is needed.

---

## Implementation

### How do I implement ACR?

ACR provides architectural patterns, not code. Implementation approaches:
1. **Build your own:** Use ACR specifications to design your governance platform
2. **Vendor solution:** Adopt commercial products that claim ACR compliance
3. **Open source tools:** Combine existing tools (OPA, OpenTelemetry, etc.) per ACR patterns
4. **Hybrid:** Implement some layers internally, use vendors for others

See [Implementation Guide](./acr-implementation-guide.md) for detailed deployment architectures.


### Do I need to implement all six ACR layers?

No. ACR layers are modular. Many organizations start with:
1. **Execution Observability** (easiest, immediate value)
2. **Behavioral Policy Enforcement** (high urgency for compliance)
3. **Add others incrementally**

However, full ACR compliance requires all six layers.

### What infrastructure do I need?

Minimum requirements:
- Access to AI model APIs (OpenAI, Anthropic, etc.)
- Observability stack (logging, metrics)
- Identity provider (OAuth, SPIFFE, or service accounts)

Recommended additions:
- Policy engine (OPA, Cedar)
- SIEM or data warehouse for audit logs
- API gateway or service mesh (for centralized enforcement)

### Can I run ACR in air-gapped environments?

Yes, with adaptations:
- Use on-premise models instead of cloud APIs
- Deploy control plane entirely within your network
- Self-hosted identity and policy engines
- Local observability stack (no cloud export)

---

## Comparison to Other Tools

### How is ACR different from LangSmith or LangFuse?

**LangSmith/LangFuse:** Observability and debugging platforms for LLM applications. They focus on tracing, logging, and performance monitoring.

**ACR:** Governance architecture that includes observability plus policy enforcement, drift detection, and automated containment. ACR is broader and focused on control, not just visibility.

**Relationship:** You could use LangSmith/LangFuse as the observability layer within an ACR implementation.

### How is ACR different from Guardrails AI?

**Guardrails AI:** Library for input/output validation and structured output generation for LLMs.

**ACR:** Full governance architecture covering identity, policy, drift, observability, containment, and human authority. Policy enforcement is one of six layers.

**Relationship:** Guardrails AI could be used as a policy enforcement mechanism within the ACR Behavioral Policy layer.

### How is ACR different from NIST AI RMF or ISO 42001?

**NIST AI RMF / ISO 42001:** Governance frameworks defining *what* organizations should do (risk management processes, policies, roles).

**ACR:** Architectural patterns for *how* to enforce those requirements at runtime in production systems.

**Relationship:** ACR implements the technical controls required by NIST/ISO. See [NIST AI RMF Mapping](../compliance/acr-nist-ai-rmf-mapping.md).

### How does ACR relate to MLOps or model governance platforms?

**MLOps platforms:** Focus on model training, versioning, deployment, and monitoring (pre-production and model-centric).

**ACR:** Focuses on runtime governance of deployed models in production (post-deployment and system-centric).

**Relationship:** MLOps handles "model release to production," ACR handles "control after release." They're complementary.

---

## Compliance & Standards

### Does ACR help with regulatory compliance?

Yes. ACR provides:
- Audit trails for AI decision-making (SOC 2, ISO compliance)
- Policy enforcement for data privacy (GDPR, HIPAA)
- Evidence bundles for regulatory audits
- Runtime controls mapped to compliance requirements

However, ACR is a technical architecture, not a legal framework. You still need compliance programs and legal counsel.

### Is ACR aligned with the EU AI Act?

ACR is designed to support EU AI Act requirements, particularly for high-risk AI systems requiring:
- Transparency and record-keeping (Observability layer)
- Human oversight (Human Authority layer)
- Accuracy and robustness monitoring (Drift Detection layer)

Detailed EU AI Act mapping is planned for v1.2 (Q3 2026).

### Can ACR help achieve SOC 2 Type II compliance?

Yes. ACR controls map to SOC 2 Trust Service Criteria:
- CC6.1 (Logical Access): Identity & Purpose Binding
- CC7.2 (System Monitoring): Execution Observability
- CC8.1 (Change Management): Drift Detection
- PI1.4 (Privacy): Behavioral Policy Enforcement

See [SOC 2 Mapping](../compliance/acr-soc2-mapping.md) (planned for v1.1).

---

## Technical Questions

### What programming languages does ACR support?

ACR is language-agnostic. It's an architectural pattern, not a library. You can implement ACR in:
- Python, JavaScript/TypeScript, Go, Java, Rust, or any language
- Using language-specific tools (Python SDK, Node.js middleware, etc.)

### How do I measure drift in AI systems?

Drift detection approaches in ACR Layer 3:
- **Statistical:** Monitor metrics (token usage, latency, error rate) for deviations from baseline
- **Embedding-based:** Measure semantic distance between current and baseline prompts
- **Behavioral:** Track changes in tool usage patterns, API calls, output characteristics

See [Autonomy Drift Detection Specification](../pillars/03-autonomy-drift-detection.md) for details.

### How do I handle policy conflicts?

ACR recommends **deny-by-default** for security/compliance policies:
- If any policy denies an action, the overall decision is deny
- For business policies, use explicit priority ordering
- Document conflict resolution rules in policy definitions

### Can ACR handle multi-model scenarios?

Yes. Approaches:
- **Unified identity:** Single agent_id for a system using multiple models
- **Model-specific policies:** Different policies for different model types
- **Federated control:** Separate control planes per model, coordinated at application layer

Multi-model orchestration patterns are planned for v1.2 (Q3 2026).

### How does ACR handle cost management?

ACR Observability layer captures:
- Token usage per request
- Cost per inference (using current pricing)
- Cost attribution by agent, user, or purpose

Self-Healing layer can enforce cost limits:
- Rate limiting when hourly spend exceeds threshold
- Alert on cost spikes
- Automatic capability restriction for cost-runaway scenarios

---

## Community & Contribution

### How can I contribute to ACR?

Contributions welcome in several areas:
- Framework enhancements (new patterns, specifications)
- Standards mappings (regulatory frameworks)
- Use cases and case studies
- Threat model expansion
- Implementation guidance

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for detailed process.

### Can I list my commercial product as ACR-compliant?

Yes, if your product implements ACR specifications. Add your product to the [Implementations section](../../README.md#implementations) via pull request with:
- Product name and description
- Which ACR layers are implemented
- Deployment patterns supported
- Link to documentation

### Are there ACR community calls?

Planned for Q2 2026. Join [GitHub Discussions](https://github.com/AdamDiStefanoAI/acr-framework/discussions) for announcements.

### How do I get support?

ACR is a framework, not a product, so there's no official support. Resources:
- [GitHub Discussions](https://github.com/AdamDiStefanoAI/acr-framework/discussions) for questions
- [GitHub Issues](https://github.com/AdamDiStefanoAI/acr-framework/issues) for clarifications
- Community implementations may offer their own support

---

## Future Development

### What's on the ACR roadmap?

See [ROADMAP.md](../../ROADMAP.md) for detailed plans. Highlights:
- **v1.1 (Q2 2026):** Detailed pillar specs, telemetry schema, deployment patterns
- **v1.2 (Q3 2026):** EU AI Act mapping, multi-model orchestration, advanced threat model
- **v1.3 (Q4 2026):** Maturity model, operational runbooks, metrics framework
- **v2.0 (2027+):** Extensions for emerging AI paradigms

### Will there be ACR certification?

Possibly in the future. For now, "ACR compliance" is self-assessed:
- Implement all six control layers
- Follow architectural patterns in specifications
- Meet evaluation criteria in each pillar spec

Formal certification program may be established if ecosystem demand warrants.

### Can I request new features or framework changes?

Yes. Process:
1. Open [GitHub Discussion](https://github.com/AdamDiStefanoAI/acr-framework/discussions) to propose idea
2. Community feedback and refinement
3. If accepted, create GitHub Issue
4. Submit pull request with specification updates

Major architectural changes require RFC (Request for Comments) and extended community review.

---

## Getting Started

### I'm new to AI governance. Where should I start?

Recommended learning path:
1. Read [ACR Framework README](../../README.md) for overview
2. Review [Use Cases](./acr-use-cases.md) for practical examples
3. Study [Execution Observability](../pillars/04-execution-observability.md) (easiest layer to understand)
4. Explore [Implementation Guide](./acr-implementation-guide.md) for deployment patterns
5. Join community discussions to ask questions

### I'm an architect. What should I read first?

Technical deep-dive path:
1. [ACR Control Plane Architecture](../architecture/acr-control-plane-architecture.md)
2. [Reference Architecture](../architecture/acr-runtime-architecture.md)
3. [Telemetry Schema Specification](../specifications/telemetry-schema.md)
4. [Implementation Guide](./acr-implementation-guide.md) for deployment patterns and options
5. [NIST AI RMF Mapping](../compliance/acr-nist-ai-rmf-mapping.md) for compliance context

### I'm a security professional. What's most relevant?

Security-focused resources:
1. [STRIKE Threat Model](../security/acr-strike-threat-model.md)
2. [Behavioral Policy Enforcement](../pillars/02-behavioral-policy-enforcement.md)
3. [Self-Healing & Containment](../pillars/05-self-healing-containment.md)
4. [Identity & Purpose Binding](../pillars/01-identity-purpose-binding.md)

### I'm a compliance officer. How does ACR help?

Compliance-focused resources:
1. [NIST AI RMF Mapping](../compliance/acr-nist-ai-rmf-mapping.md)
2. [ISO 42001 Mapping](../compliance/acr-iso42001-mapping.md) (planned v1.1)
3. [SOC 2 Mapping](../compliance/acr-soc2-mapping.md) (planned v1.1)
4. [Execution Observability](../pillars/04-execution-observability.md) for audit trails

---

Still have questions? Ask in [GitHub Discussions](https://github.com/AdamDiStefanoAI/acr-framework/discussions).
