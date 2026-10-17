# ACR Framework — Governance

This document describes how the ACR Framework project is governed: maintainer roles, decision-making, contribution process, and how the project aligns with its goal of becoming a widely adopted, community-backed standard for runtime AI governance.

---

## Project Goals

- **Authoritative:** Be the go-to reference architecture for runtime governance of autonomous AI systems.
- **Adoption-focused:** Support implementers, vendors, and auditors with clear specs, mappings, and adoption guidance (see [ADOPTION.md](ADOPTION.md)).
- **Community-driven:** Evolve through open contribution, discussions, and working groups while maintaining consistency and quality.
- **Standards-aligned:** Stay aligned with NIST AI RMF, ISO/IEC 42001, SOC 2, and emerging regulations (e.g. EU AI Act).

---

## Maintainer

**Current maintainer:** Adam DiStefano ([@AdamDiStefanoAI](https://github.com/AdamDiStefanoAI))

Responsibilities:

- Final say on merging pull requests and on scope of the framework (what belongs in "core" ACR).
- Releasing versions, maintaining [ROADMAP.md](ROADMAP.md), and representing the project in external discussions.
- Ensuring documentation quality, link integrity, and consistency across pillars and specs.
- Facilitating working groups and community input (e.g. via GitHub Issues).

As the project grows, additional maintainers or a governance board may be added and documented here.

---

## Decision-Making

- **Documentation and specs:** Changes to pillar specifications, architecture docs, and compliance mappings are merged after review. Significant changes should be discussed in an issue first.
- **Scope:** New pillars, major architectural changes, or new top-level frameworks (e.g. beyond STRIKE) require broad alignment; the maintainer may solicit feedback via issues or an RFC.
- **Roadmap:** [ROADMAP.md](ROADMAP.md) is maintained by the maintainer; input from the community (issues, pull requests) is welcome and will be considered for future versions.
- **Code of conduct:** Enforcement follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Reports go to the maintainer.

---

## Contribution Process

1. **Discuss:** For substantial changes, open a [GitHub Issue](https://github.com/AdamDiStefanoAI/acr-framework/issues) to align on approach.
2. **Contribute:** Follow [CONTRIBUTING.md](CONTRIBUTING.md). Submit a pull request with clear description and updated links/docs as needed.
3. **Review:** Maintainer (and optionally other contributors) review for accuracy, consistency with ACR principles, and impact on existing docs.
4. **Merge:** Once approved, the PR is merged. For releases, the maintainer tags a version and updates [CHANGELOG.md](CHANGELOG.md).

We welcome:

- Fixes (typos, broken links, clarifications)
- New or expanded specifications and mappings
- Use cases, case studies, and implementation patterns
- Threat model (STRIKE) expansions and refinements
- Compliance mappings (e.g. EU AI Act, sector-specific)
- Translations (coordinate via issue to avoid duplication)

---

## Working Groups (Planned)

The roadmap envisions community working groups to deepen specific areas. Potential groups:

- **Drift detection:** Metrics, baselines, and evaluation criteria for autonomy drift.
- **Policy languages:** Common policy DSL or schema for ACR-aligned rules.
- **Observability standards:** Telemetry schema evolution, OpenTelemetry alignment, and cross-org observability.

Participation would be via GitHub Issues, periodic syncs (e.g. monthly), and contributions to the repo. Formalization (charters, chairs) will be announced when launched.

---

## Relationship to Other Organizations

- ACR is an **open, community-oriented framework**, not a legal entity. It is hosted at [AdamDiStefanoAI/acr-framework](https://github.com/AdamDiStefanoAI/acr-framework).
- **NIST, ISO, OWASP, MITRE:** ACR complements these; we map to NIST AI RMF and ISO where applicable. We do not speak for those organizations.
- **Vendors and adopters:** Listing in the [Implementations](README.md#implementations) section does not imply endorsement. Adopters self-declare alignment (see [ADOPTION.md](ADOPTION.md)).

---

## Versioning and Releases

- **Semantic versioning:** Major (e.g. 2.0) for breaking or major architectural changes; minor (e.g. 1.1) for new content and backward-compatible extensions; patch for corrections and minor clarifications.
- **Releases:** Tagged in the repository with release notes; [CHANGELOG.md](CHANGELOG.md) is updated for each release.
- **Stability:** Pillar specifications and the STRIKE threat model are treated as stable references. Changes are backward-compatible where possible and called out in the changelog.

---

## References

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [ADOPTION.md](ADOPTION.md)
- [ROADMAP.md](ROADMAP.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
