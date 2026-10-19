# Ordinary README validation record

This records the public onboarding path on a separate disposable GitHub-hosted Ubuntu runner. It uses the ordinary `docker-compose.yml`, public `.env.example` development settings, and README operator-key exports. It does not use the specialized full-stack override or protected-executor fixture.

The [workflow](../.github/workflows/acr-readme-validation.yml) invokes a [recording script](../.github/scripts/acr-readme-validation.sh). The documented `docker compose up --build` runs as a supervised background process to represent Terminal 1; the health check and sample run represent Terminal 2. Timeouts, readiness probes, recording, and project-scoped teardown are CI instrumentation. They do not change application settings. Checkout replaces cloning, and the tested revision is retained.

## Failures retained before correction

1. [Workflow validation run 39208015345](https://github.com/AdamDiStefanoAI/acr-standard/actions/runs/39208015345) failed before onboarding because the new harness referenced `runner.temp` in job-level `env`. This was a workflow defect. Moving that value to supported step-level `env` fixed it; no application workaround was involved.
2. [Ordinary-path run 39208172918](https://github.com/AdamDiStefanoAI/acr-standard/actions/runs/39208172918), PR head `f103b0de688e5ae8127e91b08de74e925a98e72d`, reached a healthy gateway but failed the README's `version: 1.0` assertion. Actual output was `{"status":"healthy","version":"1.1.0","env":"development"}`. This was a documentation mismatch. Both README examples now describe the configured runtime metadata field; it is not the installed distribution version. Artifact `acr-readme-39208172918-1`, ID `12166423446`, retained the first failing health stage, commands and successful teardown.
3. [Ordinary-path run 39208428153](https://github.com/AdamDiStefanoAI/acr-standard/actions/runs/39208428153), PR head `eb8ff797c27fc3108bcfe8d3ef5c34dc07c6a2ff`, passed health and console HTTP checks and ran the sample successfully, then failed the documented `send_email` ALLOW expectation. Actual output was `[MODIFY] send_email (resolution notification)` with reason `Sensitive fields were redacted by output controls (email)`. The sample README and assertion now reflect that transformation. Artifact `acr-readme-39208428153-1`, ID `12165664627`, retained the sample output and first failing assertion. Runtime policy was not changed.

These failures remain part of the record. A later passing run does not turn either earlier revision into a passing newcomer result.

## Successful corrected run

[Run 39208714994](https://github.com/AdamDiStefanoAI/acr-standard/actions/runs/39208714994), attempt 1, completed on 2026-10-19 at 06:15 UTC, passed the corrected ordinary path and teardown on a new runner.

- PR head: `bf4175962b508d9659e13ce505209c8fa7ae7518`.
- Checked-out test merge revision: `55934111c0bd3d4fb14db9a338724f9f3d9e80b1`.
- Ubuntu 24.04, Python 3.12.15, Docker Engine 28.0.4, Docker Compose v2.38.2.
- Artifact: `acr-readme-39208714994-1`, ID `12166414323`, one-day retention.
- Gateway health returned `{"status":"healthy","version":"1.1.0","env":"development"}`; the console returned HTTP 200 and `text/html; charset=utf-8`.
- Fresh package installation, the unmodified sample script, all expected decision-label assertions and project-scoped teardown exited zero. No first-failure file was produced.

Selected unchanged lines from the actual sample output (not a fabricated terminal transcript):

```text
  ✓ [ALLOW] query_customer_db (customer C-12345)
  ~ [MODIFY] send_email (resolution notification)
    Reason: Sensitive fields were redacted by output controls (email)
  ✓ [ALLOW] create_ticket (follow-up)
  ✗ [DENY] delete_customer (should be DENIED)
  ⏳ [ESCALATE] issue_refund $250 (should ESCALATE)
  ✓ Health: {'status': 'healthy', 'version': '1.1.0', 'env': 'development'}
```

The final recorder result was:

```text
walkthrough_exit_code=0
PASS: public Compose startup, healthy response, console HTTP, and sample-agent labels.
```

## Coverage and limits

The workflow checks the documented startup, health fields, console HTML availability over HTTP, fresh virtual-environment install and sample decision labels. It records each command, exit code and output, source hashes, Python/pip/Docker/Compose versions, dependency versions, and teardown outcome. Artifacts expire after one day; the selected failure observations above are preserved here.

Console HTTP availability is not manual browser validation. The default `EXECUTE_ALLOWED_ACTIONS=false` means the sample does not send real email, issue real refunds, or call enterprise tools. Its printed six-pillar summary is not independent proof of every pillar. This run does not establish downstream effect counts, approval resolution, production safety, all supported host environments or full ACR conformance. For bounded synthetic execution and audit-chain checks, see the separate [evidence walkthrough](evidence-walkthrough.md).
