"""
ACR Control Plane — no-Docker quickstart.

Runs the guard_tool pattern against a mocked gateway in 60 seconds.
No Docker, no Postgres, no Redis. Install and run:

    pip install acr-control-plane httpx
    python quickstart_no_docker.py

The mock simulates the gateway's /acr/evaluate endpoint: it ALLOWS
refund_customer and DENIES delete_customer, the way a real policy would.
Swap the MockTransport for a real gateway URL when you are ready —
the code above the "mock" line does not change.
"""

from __future__ import annotations

import httpx

from acr.sdk import ACRClient, ACRAgentSession, ACRDeniedError, guard_tool


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
    session = ACRAgentSession(
        client=client, agent_id="support-bot", access_token="demo-token"
    )

    def refund_customer(customer_id: str, amount_usd: float) -> str:
        """Issue a refund to a customer."""
        return f"refunded ${amount_usd} to {customer_id}"

    def delete_customer(customer_id: str) -> str:
        """Delete a customer record."""
        return f"deleted {customer_id}"

    # Wrap any function: ACR authorizes it before it executes.
    refund_customer = guard_tool(refund_customer, session=session)
    delete_customer = guard_tool(delete_customer, session=session)

    # Allowed action: ACR authorizes, the function runs.
    print(refund_customer("cus_123", 25.00))

    # Forbidden action: ACR denies BEFORE the function runs. It never executes.
    try:
        delete_customer("cus_123")
    except ACRDeniedError as exc:
        print(f"DENIED before execution: {exc}")

    print("\nNext step: point ACRClient at a real gateway")
    print("(docker compose up in implementations/acr-control-plane)")
    print("and this exact code enforces real Rego policies.")


if __name__ == "__main__":
    main()
