"""SovereignOps AI - Autonomous multi-agent incident response prototype."""

from typing import TypedDict

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini

MODEL = "gemini-3.5-flash-lite"


class SandboxState(TypedDict):
    """Typed state for the synthetic private 5G environment."""

    incident_id: str
    site: str
    status: str
    latency_ms: float
    baseline_latency_ms: float
    packet_drop_pct: float
    authentication_failure_pct: float
    upf_policy_version: str
    previous_upf_policy_version: str
    suspicious_source_ip: str
    suspicious_source_isolated: bool
    amf_status: str
    smf_status: str
    upf_status: str
    actions: list[str]


# ---------------------------------------------------------------------
# SYNTHETIC PRIVATE 5G SANDBOX
# ---------------------------------------------------------------------

SANDBOX_STATE: SandboxState = {
    "incident_id": "INC-5G-001",
    "site": "Enterprise Factory Alpha",
    "status": "ACTIVE",
    "latency_ms": 184,
    "baseline_latency_ms": 18,
    "packet_drop_pct": 16.4,
    "authentication_failure_pct": 23.7,
    "upf_policy_version": "2026.08.20-rc2",
    "previous_upf_policy_version": "2026.08.13-stable",
    "suspicious_source_ip": "10.44.8.91",
    "suspicious_source_isolated": False,
    "amf_status": "HEALTHY",
    "smf_status": "HEALTHY",
    "upf_status": "DEGRADED",
    "actions": [],
}


def get_incident_telemetry(incident_id: str) -> dict:
    """
    Retrieve current telemetry for a synthetic enterprise private 5G incident.

    Use this tool before investigating an incident.

    Args:
        incident_id: Incident identifier, such as INC-5G-001.

    Returns:
        Current network telemetry and incident state.
    """

    if incident_id != SANDBOX_STATE["incident_id"]:
        return {
            "error": "Incident not found",
            "requested_incident_id": incident_id,
        }

    return dict(SANDBOX_STATE)


def execute_sandbox_remediation(action: str) -> dict:
    """
    Execute an authorized remediation against the synthetic private 5G sandbox.

    This tool NEVER changes real infrastructure.

    Allowed actions:

    - rollback_upf_policy
    - isolate_suspicious_source
    - restart_upf_service

    Args:
        action: The remediation action to execute.

    Returns:
        Result of the sandbox remediation action.
    """

    allowed_actions = {
        "rollback_upf_policy",
        "isolate_suspicious_source",
        "restart_upf_service",
    }

    if action not in allowed_actions:
        return {
            "status": "DENIED",
            "reason": "Action is not on the authorized sandbox remediation list.",
            "requested_action": action,
        }

    if action == "rollback_upf_policy":
        SANDBOX_STATE["upf_policy_version"] = SANDBOX_STATE[
            "previous_upf_policy_version"
        ]
        SANDBOX_STATE["latency_ms"] = 24
        SANDBOX_STATE["packet_drop_pct"] = 0.8
        SANDBOX_STATE["upf_status"] = "HEALTHY"

    elif action == "isolate_suspicious_source":
        SANDBOX_STATE["suspicious_source_isolated"] = True
        SANDBOX_STATE["authentication_failure_pct"] = 0.6

    elif action == "restart_upf_service":
        SANDBOX_STATE["upf_status"] = "HEALTHY"

    SANDBOX_STATE["actions"].append(action)

    return {
        "status": "EXECUTED",
        "sandbox": True,
        "action": action,
        "current_state": dict(SANDBOX_STATE),
    }


def read_sandbox_state() -> dict:
    """
    Read the current private 5G sandbox state after remediation.

    Use this tool to verify whether service has actually recovered.
    """

    recovered = (
        SANDBOX_STATE["latency_ms"] <= 30
        and SANDBOX_STATE["packet_drop_pct"] <= 1.0
        and SANDBOX_STATE["authentication_failure_pct"] <= 1.0
        and SANDBOX_STATE["upf_status"] == "HEALTHY"
    )

    if recovered:
        SANDBOX_STATE["status"] = "RESOLVED"

    return {
        "recovered": recovered,
        "state": dict(SANDBOX_STATE),
        "success_thresholds": {
            "latency_ms": "<= 30",
            "packet_drop_pct": "<= 1.0",
            "authentication_failure_pct": "<= 1.0",
            "upf_status": "HEALTHY",
        },
    }


# ---------------------------------------------------------------------
# SPECIALIST AGENTS
# ---------------------------------------------------------------------

triage_agent = Agent(
    name="triage_agent",
    model=Gemini(model=MODEL),
    mode="single_turn",
    description=(
        "Classifies telecom and enterprise incidents by severity, "
        "scope, business impact, urgency, and affected services."
    ),
    instruction="""
You are the SovereignOps Triage Agent.

Analyze the supplied private 5G incident telemetry.

Determine:

1. severity
2. affected services
3. affected infrastructure
4. customer/business impact
5. whether this appears operational, security-related, or both
6. immediate containment priorities

Do not invent telemetry.

Return a concise structured triage assessment for the orchestrator.
""",
)


investigation_agent = Agent(
    name="investigation_agent",
    model=Gemini(model=MODEL),
    mode="single_turn",
    description=(
        "Investigates telecom infrastructure telemetry and identifies "
        "probable technical root causes."
    ),
    instruction="""
You are the SovereignOps Investigation Agent.

Analyze all incident evidence supplied by the orchestrator.

Correlate:

- latency
- packet loss
- authentication failures
- core network functions
- UPF state
- recent configuration changes
- suspicious traffic indicators

Determine the most probable root cause or combination of causes.

Distinguish facts from hypotheses.

Give the orchestrator:

- primary root-cause hypothesis
- supporting evidence
- confidence level
- alternative hypotheses
- recommended technical actions
""",
)


security_policy_agent = Agent(
    name="security_policy_agent",
    model=Gemini(model=MODEL),
    mode="single_turn",
    description=(
        "Evaluates proposed incident responses against security, "
        "zero-trust, sovereignty, and operational safety policies."
    ),
    instruction="""
You are the SovereignOps Security and Policy Agent.

Evaluate the incident and proposed response.

Apply these policies:

POLICY P1:
Suspicious sources exhibiting repeated authentication failures may
be isolated.

POLICY P2:
A recently deployed network policy may be rolled back when strong
evidence links it to service degradation.

POLICY P3:
Only sandbox actions are authorized in this prototype.

POLICY P4:
Never expose credentials, secrets, private subscriber information,
or sensitive payload data.

POLICY P5:
Security protection takes precedence over performance optimization.

POLICY P6:
Every executed action must be auditable.

Determine:

- which remediation actions are authorized
- which are prohibited
- security justification
- sovereignty/compliance implications
- whether human authorization would be required in production

Return an explicit policy decision to the orchestrator.
""",
)


remediation_agent = Agent(
    name="remediation_agent",
    model=Gemini(model=MODEL),
    mode="single_turn",
    description=(
        "Executes authorized corrective actions against the synthetic "
        "private 5G sandbox."
    ),
    tools=[execute_sandbox_remediation],
    instruction="""
You are the SovereignOps Remediation Agent.

You receive:

- incident evidence
- investigation findings
- security-policy authorization

You must act, not merely recommend.

Use execute_sandbox_remediation for every authorized action required
to resolve the incident.

Available sandbox actions are:

rollback_upf_policy
isolate_suspicious_source
restart_upf_service

Do NOT attempt any action that the policy assessment has not authorized.

This prototype controls synthetic infrastructure only.

Return:

- actions attempted
- tool execution results
- actions denied or skipped
- expected recovery state
""",
)


verification_agent = Agent(
    name="verification_agent",
    model=Gemini(model=MODEL),
    mode="single_turn",
    description=(
        "Independently verifies whether remediation actually restored "
        "the private 5G service."
    ),
    tools=[read_sandbox_state],
    instruction="""
You are the SovereignOps Verification Agent.

Never assume remediation succeeded.

Call read_sandbox_state.

Verify these recovery objectives:

latency <= 30 ms
packet drop <= 1 percent
authentication failures <= 1 percent
UPF status = HEALTHY

Return either:

VERIFICATION PASSED

or

VERIFICATION FAILED

Include the measurements supporting your decision.

Only declare the incident resolved when all required thresholds pass.
""",
)


# ---------------------------------------------------------------------
# ORCHESTRATOR
# ---------------------------------------------------------------------

root_agent = Agent(
    name="sovereignops_orchestrator",
    model=Gemini(model=MODEL),
    description=(
        "Coordinates autonomous enterprise and private 5G incident "
        "investigation, policy analysis, remediation, and verification."
    ),
    tools=[get_incident_telemetry],
    sub_agents=[
        triage_agent,
        investigation_agent,
        security_policy_agent,
        remediation_agent,
        verification_agent,
    ],
    instruction="""
You are SovereignOps AI, the autonomous incident-response orchestrator.

Your objective is to investigate and resolve enterprise infrastructure
incidents safely.

For incident INC-5G-001 you MUST follow this lifecycle:

STEP 1 - OBSERVE
Call get_incident_telemetry.

STEP 2 - TRIAGE
Delegate the telemetry to the Triage Agent.

STEP 3 - INVESTIGATE
Delegate the telemetry and triage findings to the Investigation Agent.

STEP 4 - POLICY GATE
Delegate the evidence, investigation results, and proposed actions to
the Security and Policy Agent.

No remediation may occur before this policy gate.

STEP 5 - REMEDIATE
Delegate ONLY authorized actions to the Remediation Agent.

The remediation agent must execute actual sandbox tools rather than
merely describe recommendations.

STEP 6 - VERIFY
Delegate to the Verification Agent.

The verification agent must inspect the resulting sandbox state.

If verification fails, analyze the remaining problem and perform one
additional authorized remediation cycle.

STEP 7 - AUDIT

Produce a final report containing:

INCIDENT
SEVERITY
ROOT CAUSE
EVIDENCE
POLICY DECISION
ACTIONS EXECUTED
VERIFICATION RESULTS
FINAL STATUS
AUDIT TRAIL

Do not claim the incident is resolved unless the Verification Agent
has confirmed recovery.

Always clearly distinguish simulated sandbox actions from real
production actions.
""",
)


app = App(
    root_agent=root_agent,
    name="app",
)
