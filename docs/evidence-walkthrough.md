# Follow a decision into its evidence

This walkthrough uses actual captured output from a disposable GitHub-hosted test on 2026-10-19. All agent, customer and tool values are synthetic. No real customer system, email, payment or model service was used. The final tool effect was a local JSONL ledger entry.

## Source and boundaries

- [Successful run 39191938094](https://github.com/AdamDiStefanoAI/acr-standard/actions/runs/39191938094), attempt 1, completed 2026-10-19 02:53 UTC.
- PR head: `f1672e46196e634eea5c6a9941431dbadaf7e564`.
- Checked-out test merge revision recorded by the artifact: `00be86175c538b75a16beb712d8d9ca6dbad0e30`.
- Source artifact: `acr-full-stack-39191938094-1` (ID `12160242218`), retained for one day. The selected observations below are preserved here because the full artifact expires.
- These are selected complete observation objects from `observations.json`, plus the captured event and bundle manifest. No field values below were invented or rewritten. Other cases and service logs are omitted.

This is a bounded test result, not production certification or full conformance. Checksums establish content consistency; this walkthrough does not independently verify the HMAC signature. It does not prove executor replay/concurrency protection, all containment tiers, a 30-second kill SLA, or high-risk durable-log failure gating.

## 1. ALLOW: compare the decision with the actual tool effect

The HTTP response says allow. The independent fixture ledger moves from zero entries to one, with the expected tool and parameters. A decision label alone would not establish execution.

```json
{
  "case": "allow",
  "status": 200,
  "response": {
    "decision": "allow",
    "correlation_id": "cea76ec7-8a5f-41d2-bd94-06986f833c39",
    "policy_decisions": [
      {
        "policy_id": "acr-allow",
        "decision": "allow",
        "reason": null
      }
    ],
    "drift_score": null,
    "latency_ms": 29,
    "estimated_cost_usd": 0.0,
    "authoritative_hourly_spend_usd": 0.0,
    "execution_result": {
      "status": "executed",
      "authorized_by": "acr-control-plane",
      "agent_id": "full-stack-ci",
      "tool_name": "query_customer_db",
      "correlation_id": "cea76ec7-8a5f-41d2-bd94-06986f833c39",
      "approval_request_id": null,
      "credential_audience": "tool:query_customer_db",
      "credential_scopes": [
        "tool:query_customer_db:execute"
      ],
      "result": {
        "fixture": "synthetic-only",
        "sequence": 1,
        "tool_name": "query_customer_db",
        "parameters": {
          "customer_id": "C-12345"
        }
      }
    }
  },
  "before_count": 0,
  "after_count": 1,
  "new_side_effects": [
    {
      "tool_name": "query_customer_db",
      "parameters": {
        "customer_id": "C-12345"
      }
    }
  ]
}
```

## 2. DENY: verify the tool did not execute

The next request is forbidden. HTTP 403 and the policy reasons explain the refusal; the ledger stays at one entry and reports no new effect.

```json
{
  "case": "deny",
  "status": 403,
  "response": {
    "decision": "deny",
    "correlation_id": "2456683b-3d57-49fd-90f8-689ccdc5f288",
    "reason": "Customer deletion is a forbidden operation for support agents; Forbidden tool: delete_customer",
    "policy_decisions": [
      {
        "policy_id": "acr-deny-0",
        "decision": "deny",
        "reason": "Customer deletion is a forbidden operation for support agents"
      },
      {
        "policy_id": "acr-deny-1",
        "decision": "deny",
        "reason": "Forbidden tool: delete_customer"
      }
    ]
  },
  "before_count": 1,
  "after_count": 1,
  "new_side_effects": []
}
```

The denied request has its own correlation ID. The retained artifact does **not** contain that request's persisted telemetry event or exported archive. Therefore this walkthrough does not claim a complete DENY audit chain. Capturing and checking that chain remains work under [issue #25](https://github.com/AdamDiStefanoAI/acr-standard/issues/25).

## 3. Follow the captured ALLOW correlation ID

The harness exports evidence after outage and containment restoration, using a later ALLOW. Do not join this event to the first ALLOW or DENY above: their correlation IDs differ. This is the matching `restored` observation:

```json
{
  "case": "restored",
  "status": 200,
  "response": {
    "decision": "allow",
    "correlation_id": "13005686-2d6a-4872-a40d-dc032be33648",
    "policy_decisions": [
      {
        "policy_id": "acr-allow",
        "decision": "allow",
        "reason": null
      }
    ],
    "drift_score": null,
    "latency_ms": 10,
    "estimated_cost_usd": 0.0,
    "authoritative_hourly_spend_usd": 0.0,
    "execution_result": {
      "status": "executed",
      "authorized_by": "acr-control-plane",
      "agent_id": "full-stack-ci",
      "tool_name": "query_customer_db",
      "correlation_id": "13005686-2d6a-4872-a40d-dc032be33648",
      "approval_request_id": null,
      "credential_audience": "tool:query_customer_db",
      "credential_scopes": [
        "tool:query_customer_db:execute"
      ],
      "result": {
        "fixture": "synthetic-only",
        "sequence": 8,
        "tool_name": "query_customer_db",
        "parameters": {
          "customer_id": "C-12345"
        }
      }
    }
  },
  "before_count": 7,
  "after_count": 8,
  "new_side_effects": [
    {
      "tool_name": "query_customer_db",
      "parameters": {
        "customer_id": "C-12345"
      }
    }
  ]
}
```

The captured `event-chain.json` contains this event. Match `request.request_id` with the restored response's `correlation_id`, then inspect the agent, tool, parameters, output decision and timestamp.

```json
[
  {
    "agent": {
      "purpose": "Disposable full-stack checks",
      "version": null,
      "agent_id": "full-stack-ci",
      "agent_name": null,
      "capabilities": [
        "query_customer_db",
        "issue_refund"
      ],
      "identity_token_hash": null
    },
    "custom": {
      "cost_basis": "authorization_estimate",
      "estimated_cost_usd": 0.0,
      "authoritative_hourly_spend_usd": 0.0
    },
    "output": {
      "reason": null,
      "decision": "allow",
      "filtered": false,
      "filter_reason": null,
      "approval_request_id": null,
      "modified_parameters": null
    },
    "request": {
      "intent": {},
      "context": {},
      "tool_name": "query_customer_db",
      "parameters": {
        "customer_id": "C-12345"
      },
      "request_id": "13005686-2d6a-4872-a40d-dc032be33648",
      "session_id": null,
      "description": null
    },
    "event_id": "3bb3a9c0-185f-4177-b335-e8a60eb1407d",
    "metadata": {
      "integrity": {
        "payload_sha256": "f45d8965b050a7b06c780b43168b17a8319dbb8ea5ffe4b76668d7a1ead4be4f",
        "record_signature": "e4fafec548207eb3b993dc0030ae98f2f59da62534609a6b4a1e18d77575b91e",
        "signature_algorithm": "hmac-sha256",
        "previous_event_sha256": null
      },
      "drift_score": null,
      "environment": "development",
      "anomaly_flags": [],
      "compliance_tags": [],
      "acr_control_plane": {
        "version": "1.1.0",
        "enforcement_point": "gateway"
      }
    },
    "policies": [
      {
        "reason": null,
        "decision": "allow",
        "policy_id": "acr-allow",
        "latency_ms": 3,
        "policy_name": null,
        "triggered_rules": []
      }
    ],
    "execution": {
      "end_time": "2026-10-19T02:53:49.614925+00:00",
      "start_time": "2026-10-19T02:53:49.604158+00:00",
      "duration_ms": 10,
      "latency_breakdown": {
        "drift_ms": null,
        "total_ms": 10,
        "policy_ms": 3,
        "identity_ms": 5,
        "output_filter_ms": null
      }
    },
    "timestamp": "2026-10-19T02:53:49.624923+00:00",
    "event_type": "ai_inference",
    "acr_version": "1.1.0"
  }
]
```

The event's `acr_version` and control-plane version fields are captured values, not the Git revision or a claim about the package release tested. Use the pinned source revision above to identify this test.

## 4. Inspect the exported bundle

The captured ZIP contains `manifest.json`, `events.jsonl`, `checksums.sha256`, and `bundle.signature`. Its manifest is:

```json
{
  "agent_id": "full-stack-ci",
  "bundle_type": "acr-evidence-bundle",
  "correlation_id": "13005686-2d6a-4872-a40d-dc032be33648",
  "decisions": [
    "allow"
  ],
  "event_count": 1,
  "event_types": [
    "ai_inference"
  ],
  "generated_at": "2026-10-19T02:53:50.667099+00:00",
  "integrity": {
    "chain_valid": true,
    "invalid_reasons": [],
    "root_event_sha256": "f45d8965b050a7b06c780b43168b17a8319dbb8ea5ffe4b76668d7a1ead4be4f",
    "signed_events": 1,
    "verified_events": 1
  },
  "time_range": {
    "end": "2026-10-19T02:53:49.624923+00:00",
    "start": "2026-10-19T02:53:49.624923+00:00"
  }
}
```

The harness checked the downloaded archive hash and member checksums, and matched the agent, correlation ID and decision. This verifies the selected captured chain, not every possible request or cryptographic signer identity.

## Reproduce and extend

See [the full-stack validation guide](../implementations/acr-control-plane/docs/full-stack-validation.md) and the [workflow](../.github/workflows/acr-full-stack-validation.yml) for the exact disposable setup. A new run produces different identifiers and timestamps. Preserve the original failure when a run fails; do not substitute the successful values printed here.

To finish issue #25, extend the safe capture to retrieve and verify the DENY correlation's event and archive as well, then document those actual results. Never export real credentials or customer data into a public example.
