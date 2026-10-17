# ACR Framework Roadmap

This document outlines the development plan for the ACR Framework. For high-level governance and maintainer information, see the [README](README.md#framework-governance).

## Current Release: v1.0 (March 2026)

**Status:** Released

**Delivered:**

- Core six-layer control plane architecture
- Full specifications for all six pillars (Identity & Purpose Binding, Behavioral Policy Enforcement, Autonomy Drift Detection, Execution Observability, Self-Healing & Containment, Human Authority)
- NIST AI RMF mapping and ISO/IEC 42001 alignment narrative
- STRIKE threat model for AI-specific runtime threats
- Implementation guide with three reference architectures (Kubernetes+OPA, AWS Serverless+Cedar, API Gateway+Custom)
- Glossary, use cases, and FAQ
- ACR telemetry schema specification (core event structure)

## Planned Releases

### v1.1 (Q2 2026)

**Focus:** Expanded implementation patterns, standardization, and compliance detail

- **Telemetry schema standardization** — Formal versioning, optional fields, and migration guidance
- **Policy DSL requirements** — Specification for a common policy authoring format
- **Drift detection requirements** — Standard signals, baselines, and evaluation criteria
- **Deployment patterns** — Additional patterns and decision guidance in a dedicated section
- **Compliance mappings:**
  - SOC 2 Type II detailed mapping (control-by-control)
  - ISO/IEC 42001 detailed mapping (clause-by-clause)
- **Implementation guide** — Additional runbooks and operational checklists

### v1.2 (Q3 2026)

**Focus:** Multi-model orchestration and broader governance

- **Multi-model orchestration patterns** — Governance across multiple agents and model endpoints
- **Federated governance** — Cross-organization or cross-tenant ACR alignment
- **EU AI Act mapping** — Alignment with EU AI Act requirements and risk tiers
- **Extended use cases** — Deeper scenarios with sample policies and decision trees

### v2.0 (2027)

**Focus:** Extensions for emerging AI architectures and regulatory modules

- **Emerging AI architectures** — Adaptations for new agent patterns, tool-use norms, and infrastructure
- **Regulatory compliance modules** — Optional, jurisdiction-specific compliance packs
- **Community and tooling** — Mature community processes, link-check and doc CI, and optional documentation site

## Contributing to the Roadmap

Suggestions for roadmap items are welcome. Open a [GitHub Issue](https://github.com/AdamDiStefanoAI/acr-framework/issues) describing the proposed change and its rationale.
