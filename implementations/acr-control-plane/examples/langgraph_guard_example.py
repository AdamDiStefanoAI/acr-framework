"""Run deterministic tool calls through a real LangGraph graph and ACR.

See langgraph_guard_example.md for setup and the offline regression tests.
No LLM, provider API key, search service, or email service is used.
"""

from __future__ import annotations

import os

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from acr.pillar1_identity.models import AgentRegisterRequest
from acr.sdk import (
    ACRAgentSession,
    ACRClient,
    ACRDeniedError,
    AsyncACRAgentSession,
    build_langchain_tool,
)


def build_graph(
    session: ACRAgentSession | AsyncACRAgentSession,
    reports: list[str],
    external_emails: list[str],
):
    """Build the real tool graph; lists record observable local tool effects."""

    def file_report(title: str) -> str:
        """File a demo internal report in memory."""
        reports.append(title)
        return f"filed: {title}"

    def send_email_external(subject: str) -> str:
        """Record a demo external email in memory (never sends real email)."""
        external_emails.append(subject)
        return f"sent: {subject}"

    tools = [
        build_langchain_tool(file_report, session=session),
        build_langchain_tool(send_email_external, session=session),
    ]
    graph = StateGraph(MessagesState)
    # Propagate ACR denial/escalation to the caller instead of turning it into
    # a normal ToolMessage that an agent might interpret as a successful result.
    graph.add_node("tools", ToolNode(tools, handle_tool_errors=False))
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    return graph.compile()


def tool_call(tool_name: str, arguments: dict[str, str]) -> dict:
    """Supply a deterministic model-style tool call, without invoking a model."""
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": tool_name, "args": arguments, "id": "demo-call"}],
            )
        ]
    }


def main() -> None:
    # Explicit configuration avoids baking a development operator key into the
    # example. Run only against a disposable local gateway with execution off.
    operator_key = os.environ["ACR_OPERATOR_API_KEY"]
    with ACRClient(
        base_url=os.getenv("ACR_BASE_URL", "http://localhost:8000"),
        operator_api_key=operator_key,
    ) as client:
        client.ensure_agent_registered(
            AgentRegisterRequest(
                agent_id="langgraph-guard-demo",
                owner="research@example.com",
                purpose="Demonstrate allowed and denied LangGraph tool calls",
                allowed_tools=["file_report"],
                forbidden_tools=["send_email_external"],
            )
        )
        session = client.issue_agent_session("langgraph-guard-demo")
        reports: list[str] = []
        external_emails: list[str] = []
        graph = build_graph(session, reports, external_emails)

        result = graph.invoke(tool_call("file_report", {"title": "ACR demo"}))
        print(result["messages"][-1].content)
        try:
            graph.invoke(tool_call("send_email_external", {"subject": "ACR demo"}))
        except ACRDeniedError as exc:
            print(f"blocked: {exc}")
        else:
            raise RuntimeError("Expected ACR to deny send_email_external")
        if reports != ["ACR demo"] or external_emails:
            raise RuntimeError("Unexpected tool side effects")
        print(f"Side effects: reports={len(reports)}, external_emails={len(external_emails)}")


if __name__ == "__main__":
    main()
