"""The public no-Docker example checks local effects with synthetic decisions."""

from __future__ import annotations

import pytest

from examples import quickstart_no_docker as quickstart


def test_quickstart_verifies_actual_call_counts(capsys):
    quickstart.main()
    output = capsys.readouterr().out
    assert "refunded $25.0 to cus_123" in output
    assert "DENIED before execution:" in output
    assert "Verified tool calls: refund_customer=1, delete_customer=0" in output
    assert "Mocked SDK demo only" in output


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("allowed_zero", "Allowed tool must run exactly once"),
        ("allowed_twice", "Allowed tool must run exactly once"),
        ("denied_executes", "Denied tool must never run"),
        ("denied_returns", "Denied action must raise ACRDeniedError"),
    ],
)
def test_quickstart_rejects_broken_guard_behavior(monkeypatch, failure, message, capsys):
    real_guard = quickstart.guard_tool

    def broken_guard(func, *, session):
        guarded = real_guard(func, session=session)

        def call(*args, **kwargs):
            if func.__name__ == "refund_customer":
                if failure == "allowed_zero":
                    return "no tool execution"
                if failure == "allowed_twice":
                    guarded(*args, **kwargs)
            else:
                if failure == "denied_executes":
                    func(*args, **kwargs)
                if failure == "denied_returns":
                    return None
            return guarded(*args, **kwargs)

        return call

    monkeypatch.setattr(quickstart, "guard_tool", broken_guard)
    with pytest.raises(AssertionError, match=message):
        quickstart.main()
    assert "Verified tool calls:" not in capsys.readouterr().out
