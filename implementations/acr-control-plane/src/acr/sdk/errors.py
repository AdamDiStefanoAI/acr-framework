"""SDK-specific errors for client and adapter consumers."""

from __future__ import annotations

from acr.gateway.models import EvaluateResponse


class ACRSDKError(RuntimeError):
    """Base exception for SDK consumers."""


class ACRHTTPError(ACRSDKError):
    """Raised when an HTTP call fails before a normal gateway decision is returned."""

    def __init__(self, *, status_code: int, message: str, body: object | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class ACRDecisionError(ACRSDKError):
    """Base exception for non-runnable control-plane decisions."""

    def __init__(self, response: EvaluateResponse) -> None:
        message = response.reason or f"ACR decision '{response.decision}' blocked execution"
        super().__init__(message)
        self.response = response


class ACRDeniedError(ACRDecisionError):
    """Raised when ACR returns a deny decision."""


class ACREscalatedError(ACRDecisionError):
    """Raised when ACR requires human approval before execution can continue."""
