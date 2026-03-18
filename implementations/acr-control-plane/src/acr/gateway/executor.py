"""Controlled downstream execution for approved ACR actions."""
from __future__ import annotations

import httpx

from acr.common.errors import DownstreamExecutionError
from acr.config import executor_integrations, settings, tool_executor_map
from acr.gateway.executor_auth import (
    build_brokered_execution_credential,
    build_execution_headers,
)
from acr.gateway.executor_integrations import execute_integrated_action


async def execute_action(
    *,
    agent_id: str,
    tool_name: str,
    parameters: dict,
    description: str | None,
    correlation_id: str,
    approval_request_id: str | None = None,
) -> dict:
    integration = executor_integrations().get(tool_name)
    if integration:
        return await execute_integrated_action(
            agent_id=agent_id,
            tool_name=tool_name,
            parameters=parameters,
            description=description,
            correlation_id=correlation_id,
            approval_request_id=approval_request_id,
            config=integration,
        )

    routes = tool_executor_map()
    target_url = routes.get(tool_name)
    if not target_url:
        raise DownstreamExecutionError(
            f"No downstream executor route configured for tool '{tool_name}'"
        )

    payload = {
        "agent_id": agent_id,
        "tool_name": tool_name,
        "parameters": parameters,
        "description": description,
        "correlation_id": correlation_id,
        "approval_request_id": approval_request_id,
    }
    headers = build_execution_headers(
        agent_id=agent_id,
        tool_name=tool_name,
        payload=payload,
        correlation_id=correlation_id,
        approval_request_id=approval_request_id,
    )
    if settings.executor_credential_secret:
        audience = f"tool:{tool_name}"
        scopes = [f"tool:{tool_name}:execute"]
        headers["X-ACR-Credential-Audience"] = audience
        headers["X-ACR-Brokered-Credential"] = build_brokered_execution_credential(
            agent_id=agent_id,
            tool_name=tool_name,
            correlation_id=correlation_id,
            audience=audience,
            scopes=scopes,
            approval_request_id=approval_request_id,
        )
    try:
        async with httpx.AsyncClient(timeout=settings.executor_timeout_seconds) as client:
            resp = await client.post(
                target_url,
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise DownstreamExecutionError("Downstream executor returned a non-object response")
            return data
    except httpx.HTTPStatusError as exc:
        raise DownstreamExecutionError(
            f"Downstream executor returned HTTP {exc.response.status_code} for tool '{tool_name}'"
        ) from exc
    except httpx.RequestError as exc:
        raise DownstreamExecutionError(
            f"Downstream executor unreachable for tool '{tool_name}': {exc}"
        ) from exc
