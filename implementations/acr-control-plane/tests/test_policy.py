"""Pillar 2 unit tests: PII redaction and output filtering."""
from __future__ import annotations

import pytest

from acr.pillar2_policy.output_filter import filter_parameters, redact_parameters


class TestOutputFilter:
    def test_redact_ssn(self) -> None:
        params = {"notes": "Customer SSN is 123-45-6789"}
        cleaned, found = redact_parameters(params)
        assert "123-45-6789" not in cleaned["notes"]
        assert "[REDACTED]" in cleaned["notes"]
        assert "ssn" in found

    def test_redact_credit_card(self) -> None:
        params = {"body": "Card number 4111 1111 1111 1111 approved"}
        cleaned, found = redact_parameters(params)
        assert "4111" not in cleaned["body"]
        assert "credit_card" in found

    def test_clean_params_unchanged(self) -> None:
        params = {"customer_id": "C-12345", "limit": 10}
        cleaned, found = redact_parameters(params)
        assert cleaned == params
        assert found == []

    def test_nested_redaction(self) -> None:
        params = {"contact": {"email": "user@example.com", "notes": "SSN: 111-22-3333"}}
        cleaned, found = redact_parameters(params)
        assert "[REDACTED]" in cleaned["contact"]["notes"]

    def test_filter_parameters_returns_cleaned(self) -> None:
        params = {"body": "Call me at 555-123-4567"}
        result = filter_parameters("send_email", params, "corr-123")
        assert "555-123-4567" not in result.get("body", "")
