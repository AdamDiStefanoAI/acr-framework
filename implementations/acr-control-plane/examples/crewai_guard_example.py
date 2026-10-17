"""
Guard CrewAI tools with ACR runtime enforcement.

Requires: pip install acr-control-plane crewai

The pattern: wrap the function behind your CrewAI tool with guard_tool.
CrewAI calls the tool; ACR authorizes the call before it executes.
"""

from crewai.tools import tool as crewai_tool

from acr.sdk import ACRClient, guard_tool
from acr.pillar1_identity.models import AgentRegisterRequest

# --- ACR setup (once per process) -------------------------------------------
client = ACRClient(base_url="http://localhost:8000", operator_api_key="dev-operator-key")
client.ensure_agent_registered(
    AgentRegisterRequest(
        agent_id="ops-agent",
        owner="ops@example.com",
        purpose="Run governed operations tasks",
        allowed_tools=["restart_service"],
        forbidden_tools=["delete_database"],
    )
)
session = client.issue_agent_session("ops-agent")


# --- Guarded implementation --------------------------------------------------
def _restart_service_impl(service_name: str) -> str:
    """Restart a named service."""
    # ... your implementation ...
    return f"restarted {service_name}"


# Wrap it: ACR authorizes every call before it executes.
restart_service_guarded = guard_tool(_restart_service_impl, session=session)


# --- CrewAI tool surface (what the agents see) --------------------------------
@crewai_tool("restart_service")
def restart_service(service_name: str) -> str:
    """Restart a named service. Governed by ACR runtime policy."""
    return restart_service_guarded(service_name=service_name)


# Wire restart_service into your CrewAI agents as usual. Every invocation
# is authorized by ACR first: denied actions raise ACRDeniedError and the
# underlying implementation never runs.
