from __future__ import annotations

import re

from acr.policy_studio.models import PolicySimulationResponse

_SSN_PATTERN = re.compile(r"\d{3}-\d{2}-\d{4}")


def simulate_policy_draft(
    *,
    manifest: dict,
    wizard_inputs: dict,
    action: dict,
    context: dict,
) -> PolicySimulationResponse:
    reasons: list[str] = []
    matched_rules: list[str] = []

    tool_name = str(action.get("tool_name") or "")
    parameters = action.get("parameters") or {}
    allowed_tools = manifest.get("allowed_tools") or []
    forbidden_tools = manifest.get("forbidden_tools") or []
    boundaries = manifest.get("boundaries") or {}
    max_actions = int(boundaries.get("max_actions_per_minute") or 0)
    max_cost = float(boundaries.get("max_cost_per_hour_usd") or 0)
    actions_this_minute = int(context.get("actions_this_minute") or 0)
    hourly_spend_usd = float(context.get("hourly_spend_usd") or 0)

    if tool_name in forbidden_tools:
        reasons.append(f"Forbidden tool: {tool_name}")
        matched_rules.append("forbidden_tool")

    if tool_name not in allowed_tools and tool_name not in forbidden_tools:
        reasons.append(f"Unauthorized tool: {tool_name} (not in allowlist)")
        matched_rules.append("tool_not_in_allowlist")

    if max_actions and actions_this_minute > max_actions:
        reasons.append(
            f"Rate limit exceeded: {actions_this_minute} actions/min (max: {max_actions})"
        )
        matched_rules.append("rate_limit")

    if max_cost and hourly_spend_usd > max_cost:
        reasons.append(
            f"Hourly spend limit exceeded: ${hourly_spend_usd:.2f} (max: ${max_cost:.2f})"
        )
        matched_rules.append("spend_limit")

    pii_fields = [
        item.strip() for item in str(wizard_inputs.get("pii_fields") or "").split(",") if item.strip()
    ]
    if tool_name == "send_email":
        for field in pii_fields:
            value = parameters.get(field)
            if isinstance(value, str) and _SSN_PATTERN.search(value):
                reasons.append(f"PII detected in outbound {field}: SSN pattern found")
                matched_rules.append(f"pii_{field}")

    if reasons:
        return PolicySimulationResponse(
            final_decision="deny",
            reasons=reasons,
            matched_rules=matched_rules,
            manifest_summary={
                "risk_tier": manifest.get("risk_tier"),
                "allowed_tools": allowed_tools,
            },
        )

    escalate_tool = str(wizard_inputs.get("escalate_tool") or "").strip()
    approval_queue = str(wizard_inputs.get("approval_queue") or "default").strip() or "default"
    raw_threshold = str(wizard_inputs.get("escalate_over_amount") or "").strip()
    threshold = float(raw_threshold) if raw_threshold else None

    if escalate_tool and tool_name == escalate_tool:
        amount = parameters.get("amount")
        if threshold is None:
            return PolicySimulationResponse(
                final_decision="escalate",
                reasons=[f"Action requires human approval: {tool_name}"],
                approval_queue=approval_queue,
                matched_rules=["escalate_tool"],
                manifest_summary={
                    "risk_tier": manifest.get("risk_tier"),
                    "allowed_tools": allowed_tools,
                },
            )
        if isinstance(amount, (int, float)) and float(amount) > threshold:
            return PolicySimulationResponse(
                final_decision="escalate",
                reasons=[f"Amount {float(amount):.2f} exceeds escalation threshold {threshold:.2f}"],
                approval_queue=approval_queue,
                matched_rules=["escalate_threshold"],
                manifest_summary={
                    "risk_tier": manifest.get("risk_tier"),
                    "allowed_tools": allowed_tools,
                },
            )

    return PolicySimulationResponse(
        final_decision="allow",
        reasons=[],
        matched_rules=["allow_default"],
        manifest_summary={
            "risk_tier": manifest.get("risk_tier"),
            "allowed_tools": allowed_tools,
        },
    )
