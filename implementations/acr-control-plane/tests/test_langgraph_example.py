"""Real LangGraph dispatch with synthetic ACR HTTP decisions, not a live stack."""

from __future__ import annotations

import json

import httpx
import pytest

pytest.importorskip("langgraph")

from langchain_core.messages import ToolMessage  # noqa: E402

from acr.sdk import ACRClient, ACRDeniedError, AsyncACRClient  # noqa: E402
from examples.langgraph_guard_example import build_graph, tool_call  # noqa: E402


@pytest.mark.parametrize("async_mode", [False, True], ids=["invoke", "ainvoke"])
@pytest.mark.parametrize("denial_status", [200, 403])
async def test_graph_dispatch_authorizes_before_local_side_effects(async_mode, denial_status):
    reports: list[str] = []
    external_emails: list[str] = []
    evaluated: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/acr/evaluate"
        assert request.headers["Authorization"] == "Bearer synthetic-test-token"
        body = json.loads(request.content)
        assert body["agent_id"] == "langgraph-test"
        action = body["action"]
        name = action["tool_name"]
        evaluated.append(name)
        # Evaluate must precede the relevant tool's actual list mutation.
        assert external_emails == []
        if name == "file_report":
            assert reports == []
            assert action["parameters"] == {"title": "Verified report"}
            return httpx.Response(200, json={"decision": "allow"})
        assert name == "send_email_external"
        assert reports == ["Verified report"]
        assert action["parameters"] == {"subject": "Blocked email"}
        return httpx.Response(
            denial_status, json={"decision": "deny", "reason": "external email forbidden"}
        )

    async def check(client):
        session = client.create_agent_session("langgraph-test", "synthetic-test-token")
        graph = build_graph(session, reports, external_emails)
        allowed = tool_call("file_report", {"title": "Verified report"})
        result = await graph.ainvoke(allowed) if async_mode else graph.invoke(allowed)
        message = result["messages"][-1]
        assert isinstance(message, ToolMessage)
        assert message.content == "filed: Verified report"
        assert message.tool_call_id == "demo-call"
        assert reports == ["Verified report"]
        denied = tool_call("send_email_external", {"subject": "Blocked email"})
        with pytest.raises(ACRDeniedError, match="external email forbidden"):
            if async_mode:
                await graph.ainvoke(denied)
            else:
                graph.invoke(denied)
        assert external_emails == []
        assert reports == ["Verified report"]
        assert evaluated == ["file_report", "send_email_external"]

    transport = httpx.MockTransport(handler)
    if async_mode:
        async with AsyncACRClient(base_url="http://test", transport=transport) as client:
            await check(client)
    else:
        with ACRClient(base_url="http://test", transport=transport) as client:
            await check(client)
