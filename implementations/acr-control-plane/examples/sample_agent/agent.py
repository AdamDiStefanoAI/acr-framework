"""
ACR Sample Agent — demonstrates all six pillar behaviors.

Run with: python examples/sample_agent/agent.py
Requires: docker-compose up (ACR gateway running on localhost:8000)

This agent:
1. Registers itself with the ACR gateway
2. Issues a short-lived JWT and uses it for all evaluate calls
3. Executes allowed tool calls (query_customer_db, send_email, create_ticket)
4. Attempts a forbidden action (delete_customer) — demonstrates policy denial
5. Attempts a high-value refund (issue_refund amount=250) — demonstrates escalation
"""
from __future__ import annotations

import os
import sys

import httpx

ACR_GATEWAY_URL = "http://localhost:8000"
AGENT_ID = "customer-support-01"
OPERATOR_API_KEY = os.getenv("ACR_OPERATOR_API_KEY", "dev-operator-key")


def print_result(action_name: str, response: httpx.Response) -> None:
    status = response.status_code
    data = response.json()
    decision = data.get("decision", "unknown")
    symbol = {"allow": "✓", "deny": "✗", "escalate": "⏳"}.get(decision, "?")
    print(f"\n  {symbol} [{status}] {action_name}")
    print(f"    Decision: {decision}")
    if data.get("reason"):
        print(f"    Reason: {data['reason']}")
    if data.get("approval_request_id"):
        print(f"    Approval ID: {data['approval_request_id']}")
    if data.get("latency_ms"):
        print(f"    Latency: {data['latency_ms']}ms")
    if data.get("correlation_id"):
        print(f"    Correlation: {data['correlation_id']}")


def main() -> None:
    print("=" * 60)
    print("  ACR Sample Agent — Customer Support Bot")
    print("=" * 60)

    client = httpx.Client(base_url=ACR_GATEWAY_URL, timeout=10.0)
    operator_headers = {"X-Operator-API-Key": OPERATOR_API_KEY}

    # ── Step 1: Register the agent ────────────────────────────────────────────
    print("\n[1] Registering agent with ACR gateway...")
    reg_resp = client.post(
        "/acr/agents",
        headers=operator_headers,
        json={
            "agent_id": AGENT_ID,
            "owner": "support-engineering@example.com",
            "purpose": "Handle customer support tickets and issue resolutions",
            "risk_tier": "medium",
            "allowed_tools": ["query_customer_db", "send_email", "create_ticket", "issue_refund"],
            "forbidden_tools": ["delete_customer"],
            "boundaries": {
                "max_actions_per_minute": 30,
                "max_cost_per_hour_usd": 5.0,
                "credential_rotation_days": 90,
            },
        },
    )
    if reg_resp.status_code in (201, 409):
        print(f"  ✓ Agent registered (status={reg_resp.status_code})")
    else:
        print(f"  ✗ Registration failed: {reg_resp.status_code} — {reg_resp.text}")
        sys.exit(1)

    # ── Step 2: Issue a JWT and attach it to all evaluate requests ────────────
    print("\n[2] Issuing agent JWT...")
    token_resp = client.post(f"/acr/agents/{AGENT_ID}/token", headers=operator_headers)
    if token_resp.status_code != 200:
        print(f"  ✗ Token issuance failed: {token_resp.status_code} — {token_resp.text}")
        sys.exit(1)
    token_data = token_resp.json()
    access_token = token_data["access_token"]
    expires_in = token_data["expires_in_seconds"]
    print(f"  ✓ Token issued (expires in {expires_in}s)")

    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # ── Step 3: Allowed actions ───────────────────────────────────────────────
    print("\n[3] Executing allowed tool calls...")

    context = {"session_id": "sess-demo-001", "actions_this_minute": 1, "hourly_spend_usd": 0.10}

    resp = client.post("/acr/evaluate", headers=auth_headers, json={
        "agent_id": AGENT_ID,
        "action": {
            "tool_name": "query_customer_db",
            "parameters": {"customer_id": "C-12345"},
            "description": "Look up customer record",
        },
        "context": context,
    })
    print_result("query_customer_db (customer C-12345)", resp)

    context["actions_this_minute"] += 1
    resp = client.post("/acr/evaluate", headers=auth_headers, json={
        "agent_id": AGENT_ID,
        "action": {
            "tool_name": "send_email",
            "parameters": {"to": "alice@example.com", "subject": "Your ticket", "body": "We have resolved your issue."},
            "description": "Send resolution email",
        },
        "context": context,
    })
    print_result("send_email (resolution notification)", resp)

    context["actions_this_minute"] += 1
    resp = client.post("/acr/evaluate", headers=auth_headers, json={
        "agent_id": AGENT_ID,
        "action": {
            "tool_name": "create_ticket",
            "parameters": {"customer_id": "C-12345", "subject": "Follow-up required"},
            "description": "Create follow-up ticket",
        },
        "context": context,
    })
    print_result("create_ticket (follow-up)", resp)

    # ── Step 4: Forbidden action ──────────────────────────────────────────────
    print("\n[4] Attempting forbidden action (delete_customer)...")
    context["actions_this_minute"] += 1
    resp = client.post("/acr/evaluate", headers=auth_headers, json={
        "agent_id": AGENT_ID,
        "action": {
            "tool_name": "delete_customer",
            "parameters": {"customer_id": "C-12345"},
            "description": "Delete customer record",
        },
        "context": context,
    })
    print_result("delete_customer (should be DENIED)", resp)
    assert resp.json().get("decision") == "deny", "Expected policy denial!"

    # ── Step 5: High-value refund → approval escalation ───────────────────────
    print("\n[5] Requesting high-value refund (>$100 → human approval required)...")
    context["actions_this_minute"] += 1
    resp = client.post("/acr/evaluate", headers=auth_headers, json={
        "agent_id": AGENT_ID,
        "action": {
            "tool_name": "issue_refund",
            "parameters": {"customer_id": "C-12345", "amount": 250.00, "reason": "Product defect"},
            "description": "Issue $250 refund",
        },
        "context": context,
    })
    print_result("issue_refund $250 (should ESCALATE)", resp)
    assert resp.json().get("decision") == "escalate", "Expected escalation!"

    # ── Step 6: Check health ──────────────────────────────────────────────────
    print("\n[6] Checking control plane health...")
    health_resp = client.get("/acr/health")
    print(f"  ✓ Health: {health_resp.json()}")

    print("\n" + "=" * 60)
    print("  Sample agent run complete.")
    print("  All six ACR pillars exercised:")
    print("    ✓ Pillar 1: Identity — agent registered and JWT issued")
    print("    ✓ Pillar 2: Policy — tool allowlist + forbidden tool blocked")
    print("    ✓ Pillar 3: Drift — metrics recorded (async)")
    print("    ✓ Pillar 4: Observability — telemetry events logged")
    print("    ✓ Pillar 5: Containment — kill switch checked each request")
    print("    ✓ Pillar 6: Authority — refund escalated to approval queue")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    main()
