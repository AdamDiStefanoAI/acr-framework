"""
Guard a LangGraph tool with ACR runtime enforcement.

Requires: pip install acr-control-plane langgraph langchain-core

The pattern: wrap your tool function with guard_tool, then hand the
wrapped function to LangGraph as usual. ACR authorizes every invocation
before it executes. Nothing about your graph changes.
"""

from acr.sdk import ACRClient, guard_tool
from acr.pillar1_identity.models import AgentRegisterRequest

# --- ACR setup (once per process) -------------------------------------------
client = ACRClient(base_url="http://localhost:8000", operator_api_key="dev-operator-key")
client.ensure_agent_registered(
    AgentRegisterRequest(
        agent_id="research-agent",
        owner="research@example.com",
        purpose="Gather research and file reports",
        allowed_tools=["search_web", "file_report"],
        forbidden_tools=["send_email_external"],
    )
)
session = client.issue_agent_session("research-agent")


# --- Your tools, guarded -----------------------------------------------------
# Wrap any function: ACR authorizes it before it executes.
def search_web(query: str) -> str:
    """Search the web for current information."""
    # ... your implementation ...
    return f"results for: {query}"


def file_report(title: str, body: str) -> str:
    """File an internal report."""
    # ... your implementation ...
    return f"filed: {title}"


search_web = guard_tool(search_web, session=session)
file_report = guard_tool(file_report, session=session)


# --- LangGraph wiring (unchanged from your normal pattern) -------------------
# from langgraph.prebuilt import create_react_agent
#
# agent = create_react_agent("openai:gpt-4o", tools=[search_web, file_report])
#
# Every tool call the agent makes now flows through ACR first:
#   allow   -> tool runs, decision logged with correlation ID
#   deny    -> ACRDeniedError raised, tool never runs
#   escalate -> approval request created, human decides
