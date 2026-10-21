"""
ACR Control Plane — no-Docker quickstart.

Runs the guard_tool pattern against a mocked gateway in 60 seconds.
No Docker, no Postgres, no Redis. Install and run:

    pip install acr-control-plane httpx
    python quickstart_no_docker.py

The mock simulates the gateway's /acr/evaluate endpoint: it ALLOWS
refund_customer and DENIES delete_customer using synthetic HTTP 200 responses.
Counters inside the tool bodies verify one allowed call and zero denied calls.
This checks local SDK guarding only, not real Rego policy decisions, persisted
evidence, approvals, or the kill switch. For those, follow the documented
Docker Compose quick start and register an agent with a real gateway.
"""

from __future__ import annotations

import httpx

from acr.sdk import ACRAgentSession, ACRClient, ACRDeniedError, guard_tool


def _mock_gateway(request: httpx.Request) -> httpx.Response:
    """Simulates the gateway's policy decision. A real gateway runs Rego policies."""
    import json

    body = json.loads(request.content)
    tool_name = body.get("action", {}).get("tool_name", "")
    if tool_name == "delete_customer":
        return httpx.Response(
            200,
            json={
                "decision": "deny",
                "reason": "delete_customer is in the agent's forbidden_tools list",
                "error_code": "TOOL_FORBIDDEN",
                "correlation_id": "demo-corr-002",
            },
        )
    return httpx.Response(
        200,
        json={
            "decision": "allow",
            "reason": "refund_customer is in the agent's allowed_tools list",
            "correlation_id": "demo-corr-001",
            "latency_ms": 12,
        },
    )


def main() -> None:
    transport = httpx.MockTransport(_mock_gateway)
    client = ACRClient(
        base_url="http://gateway.local",
        operator_api_key="demo-key",
        client=httpx.Client(transport=transport, base_url="http://gateway.local"),
    )
    session = ACRAgentSession(client=client, agent_id="support-bot", access_token="demo-token")

    # Count executions inside the actual tool bodies, not in the wrappers.
    tool_calls = {"refund_customer": 0, "delete_customer": 0}

    def refund_customer(customer_id: str, amount_usd: float) -> str:
        """Issue a refund to a customer."""
        tool_calls["refund_customer"] += 1
        return f"refunded ${amount_usd} to {customer_id}"

    def delete_customer(customer_id: str) -> str:
        """Delete a customer record."""
        tool_calls["delete_customer"] += 1
        return f"deleted {customer_id}"

    # Wrap any function: ACR authorizes it before it executes.
    refund_customer = guard_tool(refund_customer, session=session)
    delete_customer = guard_tool(delete_customer, session=session)

    # Allowed action: ACR authorizes, the function runs.
    print(refund_customer("cus_123", 25.00))

    assert tool_calls["refund_customer"] == 1, "Allowed tool must run exactly once"

    # Forbidden action: ACR denies BEFORE the function runs. It never executes.
    denial_observed = False
    try:
        delete_customer("cus_123")
    except ACRDeniedError as exc:
        denial_observed = True
        print(f"DENIED before execution: {exc}")

    assert tool_calls["delete_customer"] == 0, "Denied tool must never run"
    assert denial_observed, "Denied action must raise ACRDeniedError"
    print(
        f"Verified tool calls: refund_customer={tool_calls['refund_customer']}, "
        f"delete_customer={tool_calls['delete_customer']}"
    )
    print("Mocked SDK demo only: no real policy engine or persisted evidence was tested.")

    print("\nNext step: follow the Docker Compose quick start in the README")
    print("and register an agent with a real gateway to exercise real Rego policies.")


if __name__ == "__main__":
    main()
