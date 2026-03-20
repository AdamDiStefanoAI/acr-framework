# ACR Control Plane — Orchestrator Integration Guide

This guide explains how to place the ACR control plane underneath tools like `n8n`, LangGraph, custom agent runtimes, or internal workflow builders.

The key design choice is:

**ACR should be the mandatory enforcement layer for sensitive actions, not an optional best-practice inside each workflow.**

## The Operational Model

Think in terms of two layers:

- Experience layer: the orchestration tool, agent framework, or workflow builder your team uses
- Enforcement layer: the ACR control plane and protected executors that decide whether a real action is allowed to run

That means builders can keep using familiar tools, but high-impact actions only succeed if they pass through ACR.

## Recommended Architecture

```text
Orchestrator / Agent Runtime
    |
    | Step decides "send email", "issue refund", "create ticket"
    v
POST /acr/evaluate
    |
    +--> allow     -> gateway calls protected executor
    +--> deny      -> orchestrator receives deny and stops
    +--> escalate  -> human approval queue
    |
    v
Protected Executor / Internal API
```

## What Should Go Through ACR

Route these action classes through the control plane:

- customer-impacting changes
- ticketing and case management
- payments, refunds, credits, or billing actions
- production infrastructure actions
- internal data access outside low-risk read-only retrieval
- outbound communications to customers or partners

Low-risk internal reasoning steps do not need to call ACR directly. Real-world action boundaries do.

## Integration Contract

For each sensitive tool in your orchestrator:

1. Register the agent in ACR with its allowed tools and boundaries.
2. Issue an agent token for runtime use.
3. Replace the tool's direct downstream call with a call to `POST /acr/evaluate`.
4. Let the gateway decide `allow`, `deny`, or `escalate`.
5. If `EXECUTE_ALLOWED_ACTIONS=true`, let the gateway call the protected executor itself.
6. If approvals are required, let operators resolve them through ACR before execution continues.

## Why This Must Be Mandatory

If every builder has to remember to "use ACR when appropriate", then governance becomes optional and bypassable.

The stronger pattern is:

- orchestration tools can compose logic freely
- protected systems only accept gateway-authorized execution
- ACR is the only path to real side effects

That is what makes the control plane infrastructure rather than documentation.

## n8n Pattern

For `n8n`, treat ACR as a policy-and-execution gateway in front of sensitive nodes.

Recommended node flow:

1. Trigger or workflow logic
2. Prepare action payload
3. HTTP Request node -> `POST /acr/evaluate`
4. Switch on `decision`
5. `allow`:
   If gateway-managed execution is enabled, continue using the returned execution result
6. `deny`:
   Stop the workflow and surface the reason
7. `escalate`:
   Create a human task, pause, or notify operators using the approval request ID

If you want a reference shape, see:

- [n8n README](/Users/adamdistefano/Desktop/control_plane/examples/n8n/README.md)
- [n8n workflow JSON](/Users/adamdistefano/Desktop/control_plane/examples/n8n/acr_sensitive_action_workflow.json)

## Protected Executor Pattern

The orchestrator should not call protected systems directly for sensitive actions.

Instead:

- the gateway evaluates the request
- the gateway mints short-lived execution authorization
- the protected executor verifies the authorization and payload binding
- the protected executor calls the internal business function

Reference implementation:

- [protected executor app](/Users/adamdistefano/Desktop/control_plane/examples/protected_executor/app.py)
- [protected executor guide](/Users/adamdistefano/Desktop/control_plane/examples/protected_executor/README.md)

## Adoption Guidance For Non-Engineering Teams

If your audience is not highly technical, position ACR like this:

- teams can design workflows in their normal tools
- governance is already built into the execution path
- sensitive actions route through one approved control layer
- operators use one place for approvals, evidence, containment, and policy

That keeps user education focused on workflow design, while enforcement stays centralized.

## Minimum Production Bar

Before claiming orchestrator integration is production-ready, confirm:

- all sensitive workflow steps call `POST /acr/evaluate`
- protected executors reject direct calls that lack ACR authorization
- agents cannot reach internal systems directly with standing credentials
- approval-required actions stop at ACR instead of self-executing in the orchestrator
- evidence bundles capture the decision chain for one workflow run

## What This Repo Implements Today

This repo already provides:

- the gateway decision API
- approval workflows
- evidence export
- protected executor verification helpers
- example executor app

This guide adds the adoption model around those pieces so teams can deploy ACR as a real infrastructure layer under orchestration systems.
