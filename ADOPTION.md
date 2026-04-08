# ACR Standard — Adoption and Implementation

This document explains how to adopt the ACR Framework, how to claim alignment, how to be listed as an implementation, and how to cite and use ACR branding. The goal is to make ACR a recognizable, credible standard for runtime AI governance—similar in adoption and trust to OWASP, MITRE ATT&CK, and NIST frameworks.

---

## Who Should Adopt ACR?

- **Enterprises** running autonomous AI systems (agents, copilots, workflow automation) who need runtime governance
- **Vendors** building AI governance, observability, or policy enforcement products
- **Auditors and compliance teams** who need a technical control framework aligned to NIST AI RMF, ISO 42001, SOC 2
- **Researchers and standards bodies** working on AI safety, accountability, and operational control

---

## ACR Maturity Levels

Use these levels to stage adoption and to describe how fully a system implements ACR.

| Level | Name | Criteria | Typical Use |
|-------|------|----------|-------------|
| **Level 1** | Observability & Policy | Identity binding (or equivalent), behavioral policy enforcement, execution observability with ACR-aligned telemetry. | First phase of adoption; audit trail and basic guardrails. |
| **Level 2** | Detection & Containment | Level 1 plus autonomy drift detection and self-healing/containment (e.g. throttle, restrict, kill switch). | Reducing risk from drift and misuse. |
| **Level 3** | Full ACR | All six pillars implemented: Identity & Purpose Binding, Behavioral Policy Enforcement, Autonomy Drift Detection, Execution Observability, Self-Healing & Containment, Human Authority. | Full runtime governance; compliance and high-risk use cases. |

**Claiming a level:** You may state that your system is "ACR Level 1 (or 2 or 3) aligned" if it meets the criteria above. Implementation details can vary (see [Implementation Guide](docs/guides/acr-implementation-guide.md)). We encourage documenting which pillars and patterns you use.

---

## What "ACR-Aligned" Means

- **Aligned:** Your design and controls map to ACR pillars and intent; you implement a subset or full set of the control layers and follow the architectural patterns (control plane, telemetry, policy enforcement, etc.).
- **Not a certification:** ACR does not currently offer formal certification. Alignment is self-assessed. We recommend documenting your mapping (e.g. which pillars, which STRIKE threats you address).
- **Not a trademark claim:** "ACR" and "ACR Framework" refer to this open framework. You may describe your product or system as "ACR-aligned" or "implementing ACR patterns" in a truthful, non-misleading way.

---

## Listing Your Implementation

We maintain a list of implementations (open source, commercial, and research) in the [README](README.md#implementations). To be listed:

1. **Open a pull request** that adds your implementation to the appropriate section (Open Source, Commercial, or Research).
2. **Include:**
   - Name and short description
   - Which ACR pillars you implement (and maturity level if applicable)
   - Deployment pattern(s): e.g. API Gateway, SDK, Sidecar, Control Plane Service
   - Link to documentation or product page
3. **Acceptance:** Maintainers will review for relevance and accuracy. Listing does not imply endorsement of your product—only that you have stated alignment with ACR.

**Template for listing:**

```markdown
- **[Your Name](https://...)** — Short description. Pillars: 1, 2, 4 (Level 1). Pattern: API Gateway. [Docs](https://...)
```

---

## Badge and Logo Usage

### Badge (Markdown)

You may use this badge in READMEs or docs to indicate ACR alignment:

```markdown
[![ACR Aligned](https://img.shields.io/badge/ACR-Aligned-blue)](https://github.com/SynergeiaLabs/acr-framework)
```

Optional: specify level (e.g. "ACR Level 2 Aligned") in your own text; the badge links to the framework repo.

### Logo

If we release an official logo (e.g. in `docs/images/` or a branding repo), you may use it to link to the ACR Framework or to indicate alignment, provided you do not imply endorsement or certification. Do not modify the logo in a way that suggests official partnership unless agreed.

### Guidelines

- Use the badge/logo in a way that is accurate (you have actually implemented ACR-aligned controls).
- Do not use ACR branding in a way that suggests formal certification or that the ACR project endorses your product.
- When in doubt, use "ACR-aligned" in text and link to this repository.

---

## Citation

For papers, reports, and standards:

**BibTeX:**

```bibtex
@misc{acr-framework-2026,
  author       = {DiStefano, Adam},
  title        = {ACR Standard: Agentic Control at Runtime},
  year         = {2026},
  publisher    = {GitHub},
  journal      = {GitHub repository},
  howpublished = {\url{https://github.com/AdamDiStefaniAI/acr-framework}},
  version      = {1.0}
}
```

**Plain text:**  
ACR Standard: Agentic Control at Runtime. DiStefano, A. (2026). https://github.com/AdamDiStefanoAI/acr-framework. Version 1.0.

**STRIKE threat model:** When referencing the threat model specifically, cite "STRIKE Threat Model (ACR Standard)" and link to [docs/security/acr-strike-threat-model.md](docs/security/acr-strike-threat-model.md).

---

## Case Studies and Community

- **Case studies:** We welcome adoption stories (anonymized or with permission). Open an issue or discussion with the tag `case-study` or submit a PR that adds a short narrative under `docs/guides/` or a dedicated case-studies section.
- **Speaking and events:** If you present on ACR at conferences or meetups, we encourage you to share links or slides via Discussions or a PR to a "Presentations" or "Community" section if we add one.
- **Working groups:** Roadmap includes working groups on drift detection, policy languages, and observability standards. See [ROADMAP.md](ROADMAP.md) and [GOVERNANCE.md](GOVERNANCE.md).

---

## References

- [ACR Standard README](README.md)
- [Implementation Guide](docs/guides/acr-implementation-guide.md)
- [STRIKE Threat Model](docs/security/acr-strike-threat-model.md)
- [NIST AI RMF Mapping](docs/compliance/acr-nist-ai-rmf-mapping.md)
- [Governance](GOVERNANCE.md)
