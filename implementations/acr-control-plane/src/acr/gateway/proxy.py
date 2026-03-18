"""
Gateway proxy — mock resource forwarding for v1.

Per spec: "No real downstream proxy. The gateway evaluates and returns
allow/deny. It does not actually proxy HTTP traffic to downstream services in v1."

This module provides the interface used by the router so it can be wired to a
real proxy in a future version.
"""
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


async def forward_action(
    tool_name: str,
    parameters: dict,
    correlation_id: str,
) -> dict:
    """
    Mock forward of an approved action to the downstream resource.
    In v1 this returns a synthetic result; swap for a real httpx call in v2.
    """
    logger.info(
        "action_forwarded",
        tool_name=tool_name,
        correlation_id=correlation_id,
    )
    return {
        "tool_name": tool_name,
        "status": "executed",
        "result": f"[mock] {tool_name} executed successfully",
        "correlation_id": correlation_id,
    }
