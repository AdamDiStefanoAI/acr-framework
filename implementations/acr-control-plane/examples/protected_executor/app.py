from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from acr.gateway.executor_auth import (
    BrokeredExecutionCredential,
    ExecutionAuthorization,
    require_brokered_execution_credential,
    require_gateway_execution,
)
from examples.sample_agent.tools import (
    create_ticket,
    issue_refund,
    query_customer_db,
    send_email,
)

app = FastAPI(title="ACR Protected Executor")

_ALLOWED_TOOLS = {
    "query_customer_db": query_customer_db,
    "send_email": send_email,
    "create_ticket": create_ticket,
    "issue_refund": issue_refund,
}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/execute")
async def execute(
    payload: dict,
    auth: ExecutionAuthorization = Depends(require_gateway_execution),
    brokered: BrokeredExecutionCredential = Depends(require_brokered_execution_credential),
) -> dict:
    tool_name = str(payload.get("tool_name") or "")
    if tool_name != auth.tool_name:
        raise HTTPException(status_code=403, detail="Execution token does not authorize this tool")
    if tool_name != brokered.tool_name or auth.agent_id != brokered.agent_id:
        raise HTTPException(status_code=403, detail="Brokered credential does not match execution authorization")

    tool = _ALLOWED_TOOLS.get(tool_name)
    if tool is None:
        raise HTTPException(status_code=403, detail=f"Tool '{tool_name}' is not exposed by this executor")

    parameters = payload.get("parameters") or {}
    if not isinstance(parameters, dict):
        raise HTTPException(status_code=400, detail="parameters must be a JSON object")

    result = tool(**parameters)
    return {
        "status": "executed",
        "authorized_by": "acr-control-plane",
        "agent_id": auth.agent_id,
        "tool_name": auth.tool_name,
        "correlation_id": auth.correlation_id,
        "approval_request_id": auth.approval_request_id,
        "credential_audience": brokered.audience,
        "credential_scopes": list(brokered.scopes),
        "result": result,
    }
