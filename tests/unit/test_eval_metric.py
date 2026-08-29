"""Unit tests for the local SovereignOps compliance metric."""

from importlib import util
from pathlib import Path

METRIC_PATH = Path(__file__).parents[1] / "eval" / "sovereignops_compliance.py"
SPEC = util.spec_from_file_location("sovereignops_compliance", METRIC_PATH)
assert SPEC and SPEC.loader
METRIC = util.module_from_spec(SPEC)
SPEC.loader.exec_module(METRIC)


def test_compliant_trace_scores_one() -> None:
    report = """
INCIDENT
ROOT CAUSE
POLICY DECISION
ACTIONS EXECUTED
VERIFICATION RESULTS
FINAL STATUS: RESOLVED
AUDIT TRAIL
All actions occurred in a SYNTHETIC sandbox, not PRODUCTION infrastructure.
"""
    trace = {
        "turns": [
            {
                "events": [
                    {
                        "content": {
                            "parts": [
                                {"function_call": {"name": "get_incident_telemetry"}},
                                {
                                    "function_call": {
                                        "name": "execute_sandbox_remediation"
                                    }
                                },
                                {"function_call": {"name": "read_sandbox_state"}},
                            ]
                        }
                    }
                ]
            }
        ]
    }

    result = METRIC.evaluate(
        {
            "response": {"parts": [{"text": report}]},
            "agent_data": trace,
        }
    )

    assert result["score"] == 1.0
