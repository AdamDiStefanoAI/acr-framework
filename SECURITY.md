# Security Policy

## Supported Versions

We release patches for the current major/minor version. Security-related updates are applied to the latest release branch.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

The ACR Framework is primarily a **documentation and specification** repository, but it also includes a runnable reference implementation under `implementations/acr-control-plane/` (for local demos). If you believe you have found a security issue, it may fall into one of these categories:

1. **Vulnerability in the framework specification** — e.g. a control or design that could encourage insecure implementations.
2. **Vulnerability in documentation or examples** — e.g. sample configuration or code that could lead to misuse.
3. **Vulnerability in reference implementation / tooling** — e.g. the runnable control-plane code and related scripts (or any CI/automation we add that touches it).

**How to report:**

- **Preferred:** Open a [GitHub Security Advisory](https://github.com/SynergeiaLabs/acr-framework/security/advisories/new) (private, not visible until disclosure).
- **Alternative:** Email the maintainer (see [README](README.md#framework-governance)) with a clear description, steps to reproduce (if applicable), and impact. Do not open a public issue for unfixed security vulnerabilities.

We will acknowledge receipt within a few days and will work with you on disclosure timing. We support coordinated disclosure and will credit reporters when the issue is fixed and disclosed (unless you prefer to remain anonymous).

## Security-Related Discussions

For general security questions, threat model improvements, or control design discussions, use [GitHub Discussions](https://github.com/SynergeiaLabs/acr-framework/discussions) with the appropriate topic.
