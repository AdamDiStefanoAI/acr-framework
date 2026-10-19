"""Unit checks for transport-only retries in the acceptance harness."""

import importlib.util
from http.client import RemoteDisconnected
from pathlib import Path

import pytest


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = Path(__file__).resolve().parents[1] / "scripts/full_stack_validation.py"
    spec = importlib.util.spec_from_file_location("full_stack_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    return module


@pytest.mark.parametrize("error", [ConnectionResetError(), RemoteDisconnected()])
def test_readiness_retries_transport_failure(harness, monkeypatch, error):
    attempts = []

    def ledger():
        attempts.append(1)
        if len(attempts) == 1:
            raise error
        return []

    monkeypatch.setattr(harness, "ledger", ledger)
    harness.wait_for_executor()
    assert len(attempts) == 2


def test_readiness_rejects_invalid_ledger(harness, monkeypatch):
    def invalid():
        raise AssertionError("bad ledger")

    monkeypatch.setattr(harness, "ledger", invalid)
    with pytest.raises(AssertionError, match="bad ledger"):
        harness.wait_for_executor()


def test_readiness_timeout_fails(harness, monkeypatch):
    ticks = iter([0, 61])
    monkeypatch.setattr(harness.time, "monotonic", lambda: next(ticks))
    with pytest.raises(AssertionError, match="within 60 seconds"):
        harness.wait_for_executor()
