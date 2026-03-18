"""Pillar 2: Output filtering — PII redaction applied to action parameters."""
from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# PII patterns — applied to string values in parameters
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
]

_REDACTION = "[REDACTED]"


def _redact_string(value: str) -> tuple[str, list[str]]:
    """Redact PII patterns from a string. Returns (cleaned_value, list_of_redacted_types)."""
    found: list[str] = []
    for pii_type, pattern in _PII_PATTERNS:
        if pattern.search(value):
            value = pattern.sub(_REDACTION, value)
            found.append(pii_type)
    return value, found


def _redact_value(value: Any) -> tuple[Any, list[str]]:
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, dict):
        return redact_parameters(value)
    if isinstance(value, list):
        result = []
        all_found: list[str] = []
        for item in value:
            cleaned, found = _redact_value(item)
            result.append(cleaned)
            all_found.extend(found)
        return result, all_found
    return value, []


def redact_parameters(params: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """
    Recursively redact PII from a parameter dict.
    Returns (cleaned_params, list_of_redacted_pii_types).
    """
    cleaned: dict[str, Any] = {}
    all_found: list[str] = []
    for key, val in params.items():
        new_val, found = _redact_value(val)
        cleaned[key] = new_val
        all_found.extend(found)
    return cleaned, list(set(all_found))


def filter_parameters(
    tool_name: str,
    parameters: dict[str, Any],
    correlation_id: str,
) -> dict[str, Any]:
    """
    Apply PII redaction to action parameters before forwarding.
    Logs any redactions made.
    """
    cleaned, redacted_types = redact_parameters(parameters)
    if redacted_types:
        logger.warning(
            "pii_redacted",
            tool_name=tool_name,
            correlation_id=correlation_id,
            redacted_types=redacted_types,
        )
    return cleaned
