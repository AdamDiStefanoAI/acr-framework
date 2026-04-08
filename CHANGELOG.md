# Changelog

All notable changes to the ACR Standard documentation and repository are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0] - 2026-03

### Added

- Initial release of the ACR Standard (Agentic Control at Runtime).
- Six pillar specifications: Identity & Purpose Binding, Behavioral Policy Enforcement, Autonomy Drift Detection, Execution Observability, Self-Healing & Containment, Human Authority.
- Control plane and runtime architecture documentation.
- Implementation guide with reference architectures (Kubernetes+OPA, AWS Serverless+Cedar, API Gateway+Custom).
- STRIKE threat model for AI-specific runtime threats.
- NIST AI RMF mapping and alignment narrative.
- Glossary, use cases, and FAQ.
- Telemetry schema specification (ACR event structure).
- CONTRIBUTING.md, ROADMAP.md, SECURITY.md, CODE_OF_CONDUCT.md.
- Documentation reorganized under `docs/` (pillars, architecture, specifications, compliance, security, guides).
- GitHub Actions workflow for markdown link checking.
- Issue templates for bug reports and feature requests.
- **Adoption and credibility (post-structure):**
  - ADOPTION.md: maturity levels (1–3), "ACR-aligned" criteria, implementation listing process, badge and citation guidelines.
  - GOVERNANCE.md: project goals, maintainer role, decision-making, contribution process, working groups (planned).
  - STRIKE threat model expanded: attack scenarios, likelihood/impact, detection techniques, and detailed ACR control mapping per threat (S–T–R–I–K–E).
  - NIST AI RMF subcategory-level mapping (Govern, Map, Measure, Manage) with ACR controls and references.
  - Use cases: concrete scenarios for customer support, incident response, and financial analysis (sample policies, decision flows).
  - Persona-based Get Started in docs (Architect, Security, Compliance, Implementer, Evaluator) with 3–5 step paths.
  - Glossary expanded: Control Layer/Pillar, Policy Engine, Telemetry Schema, Kill Switch, Break-Glass, Purpose Binding, STRIKE mnemonic, ACR Maturity Level.
  - README: "Why ACR?" positioning (OWASP/MITRE-style), adoption and governance links, citation and branding section, implementations section updated with ADOPTION reference.
  - Pull request template for documentation and spec changes.

[1.0]: https://github.com/AdamDiStefanoAI/acr-framework/releases/tag/v1.0
