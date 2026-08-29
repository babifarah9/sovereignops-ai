"""Tests that deterministic sandbox tools emit audit records."""

from copy import deepcopy

import pytest

from app import agent


@pytest.fixture(autouse=True)
def restore_sandbox_state():
    original = deepcopy(agent.SANDBOX_STATE)
    yield
    agent.SANDBOX_STATE.clear()
    agent.SANDBOX_STATE.update(original)


def test_remediation_and_verification_are_audited(monkeypatch) -> None:
    events: list[tuple[str, str, dict, str | None]] = []

    def capture(incident_id, event_type, payload, *, status=None):
        events.append((incident_id, event_type, payload, status))
        return "event-id"

    monkeypatch.setattr(agent, "record_audit_event", capture)

    agent.get_incident_telemetry("INC-5G-001")
    agent.execute_sandbox_remediation("rollback_upf_policy")
    agent.execute_sandbox_remediation("isolate_suspicious_source")
    result = agent.read_sandbox_state()

    assert result["recovered"] is True
    assert [event[1] for event in events] == [
        "incident_observed",
        "remediation_executed",
        "remediation_executed",
        "verification_completed",
    ]
    assert events[-1][3] == "RESOLVED"


@pytest.mark.asyncio
async def test_each_workflow_run_resets_the_sandbox() -> None:
    class Context:
        def __init__(self) -> None:
            self.state: dict = {}

    context = Context()

    agent.SANDBOX_STATE["status"] = "RESOLVED"
    agent.SANDBOX_STATE["latency_ms"] = 24
    agent.SANDBOX_STATE["actions"].append("rollback_upf_policy")

    await agent.reset_sandbox_state(context)

    assert agent.SANDBOX_STATE == agent.INITIAL_SANDBOX_STATE
    assert agent.SANDBOX_STATE is not agent.INITIAL_SANDBOX_STATE
    assert context.state["incident_id"] == "INC-5G-001"
