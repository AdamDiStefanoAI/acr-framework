# Contributing to ACR Framework

Thank you for your interest in contributing to the ACR (Autonomous Control & Resilience) Framework. ACR is an open reference architecture for runtime governance of autonomous AI systems. Contributions to specifications, design patterns, and documentation are welcome.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.

## How to Contribute

### Contribution Areas

- **Control layer refinements and extensions** — Improve pillar specifications, add implementation patterns, or propose new control objectives
- **Implementation pattern documentation** — Document deployment patterns, technology integrations, or migration approaches
- **Threat model expansion** — New attack vectors, mitigations, detection strategies, or STRIKE category refinements
- **Standards mappings** — EU AI Act, sector-specific regulations, or deeper NIST/ISO/SOC 2 mappings
- **Case studies and deployment experiences** — Real-world adoption stories (anonymized or with permission)
- **Research and open questions** — Drift detection methods, policy languages, observability schemas

### Contribution Process

1. **Review existing issues and discussions**  
   Check [GitHub Issues](https://github.com/SynergeiaLabs/acr-framework/issues) and [GitHub Discussions](https://github.com/SynergeiaLabs/acr-framework/discussions) to see if your idea is already under discussion.

2. **Open an issue**  
   Describe your proposed contribution, the problem it addresses, and how it aligns with ACR principles. For large changes, discuss the approach before submitting a pull request.

3. **Discuss approach and alignment**  
   Maintainers and the community will review and may suggest adjustments to align with the framework’s scope and structure.

4. **Submit a pull request**  
   - Branch from `main`  
   - Update documentation in the appropriate location under [docs/](docs/)  
   - Follow the existing markdown style and structure  
   - Keep changes focused; prefer multiple small PRs over one large one  

5. **Community review and merge**  
   Maintainers will review your PR. Address feedback and ensure any link or path updates are consistent with the [docs/](docs/) layout.

### Code Contributions

ACR is an **architectural framework**. The core repository focuses on specifications, design patterns, and architectural guidance. Reference implementations are welcome and may live in this repo under `implementations/` or be linked from the [Implementations](README.md#implementations) section via a pull request.

### Documentation Structure

- **Pillar specifications:** [docs/pillars/](docs/pillars/)
- **Architecture:** [docs/architecture/](docs/architecture/)
- **Specifications:** [docs/specifications/](docs/specifications/)
- **Compliance:** [docs/compliance/](docs/compliance/)
- **Security:** [docs/security/](docs/security/)
- **Guides:** [docs/guides/](docs/guides/)
- **Images:** [docs/images/](docs/images/)

When adding or moving documents, update internal links so they work from the new paths (e.g. from `docs/pillars/` use `../architecture/` for architecture docs and `../../README.md` for the repo root).

### Pull Request Guidelines

- Use clear, descriptive titles and descriptions
- Reference any related issues
- Ensure all internal links are valid (see [ROADMAP](ROADMAP.md) for tooling plans)
- For specification changes, consider impact on existing implementations and the [Implementation Guide](docs/guides/acr-implementation-guide.md)

### Questions

- **Architecture and design:** [GitHub Discussions](https://github.com/SynergeiaLabs/acr-framework/discussions)
- **Bugs and clarifications:** [GitHub Issues](https://github.com/SynergeiaLabs/acr-framework/issues)

Thank you for helping advance runtime governance for autonomous AI systems.
