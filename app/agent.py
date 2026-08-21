"""SovereignOps AI - Autonomous multi-agent incident response prototype."""

from typing import TypedDict

from google.adk.agents import Agent, SequentialAgent
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
# DETERMINISTIC SOVEREIGNOPS WORKFLOW
# ---------------------------------------------------------------------


triage_agent = Agent(
    name="triage_agent",
    model=Gemini(model=MODEL),
    description="Observes and triages a private 5G incident.",
    tools=[get_incident_telemetry],
    output_key="triage_result",
    instruction="""
You are the SovereignOps Triage Agent.

For incident INC-5G-001, you MUST first call get_incident_telemetry.

Analyze only the retrieved evidence.

Return a structured report containing:

INCIDENT ID
SITE
SEVERITY
RAW TELEMETRY
AFFECTED SERVICES
AFFECTED INFRASTRUCTURE
BUSINESS IMPACT
SECURITY INDICATORS
IMMEDIATE PRIORITIES

Include the important numeric telemetry because subsequent agents
will use your output as evidence.

Do not invent data.
""",
)


investigation_agent = Agent(
    name="investigation_agent",
    model=Gemini(model=MODEL),
    description="Determines the technical and security root cause.",
    output_key="investigation_result",
    instruction="""
You are the SovereignOps Investigation Agent.

The Triage Agent produced this evidence:

--- TRIAGE RESULT ---
{triage_result}
--- END TRIAGE RESULT ---

Determine:

1. primary root-cause hypothesis
2. supporting evidence
3. confidence level
4. alternative hypotheses
5. relationship between configuration changes and degradation
6. significance of suspicious authentication activity
7. recommended remediation actions

Clearly distinguish facts from hypotheses.

Do not execute remediation.
""",
)


security_policy_agent = Agent(
    name="security_policy_agent",
    model=Gemini(model=MODEL),
    description="Applies the mandatory SovereignOps security policy gate.",
    output_key="policy_result",
    instruction="""
You are the SovereignOps Security and Policy Agent.

TRIAGE:
{triage_result}

INVESTIGATION:
{investigation_result}

Apply these mandatory policies:

P1:
Suspicious sources exhibiting repeated authentication failures may
be isolated.

P2:
A recently deployed network policy may be rolled back when strong
evidence links it to service degradation.

P3:
Only synthetic sandbox actions are authorized in this prototype.

P4:
Never expose credentials, secrets, subscriber private information,
or sensitive payload data.

P5:
Security protection takes precedence over performance optimization.

P6:
Every executed action must be auditable.

Evaluate the investigation recommendations.

Return:

AUTHORIZED ACTIONS
PROHIBITED ACTIONS
SECURITY JUSTIFICATION
SOVEREIGNTY / COMPLIANCE ASSESSMENT
PRODUCTION HUMAN-APPROVAL REQUIREMENTS

Only authorize actions justified by the available evidence.
""",
)


remediation_agent = Agent(
    name="remediation_agent",
    model=Gemini(model=MODEL),
    description="Executes policy-authorized remediation in the sandbox.",
    tools=[execute_sandbox_remediation],
    output_key="remediation_result",
    instruction="""
You are the SovereignOps Remediation Agent.

INCIDENT TRIAGE:
{triage_result}

ROOT-CAUSE ANALYSIS:
{investigation_result}

MANDATORY POLICY DECISION:
{policy_result}

Execute the actions explicitly authorized by the Security and Policy
Agent.

Available sandbox actions:

- rollback_upf_policy
- isolate_suspicious_source
- restart_upf_service

You MUST call execute_sandbox_remediation for required authorized actions.

Do not merely recommend an action.

Do not execute prohibited or unauthorized actions.

All actions affect synthetic infrastructure only.

Return:

ACTIONS EXECUTED
TOOL RESULTS
ACTIONS SKIPPED
REASON FOR EACH ACTION
EXPECTED RECOVERY STATE
""",
)


verification_agent = Agent(
    name="verification_agent",
    model=Gemini(model=MODEL),
    description="Independently verifies recovery and generates the audit report.",
    tools=[read_sandbox_state],
    output_key="verification_result",
    instruction="""
You are the SovereignOps Independent Verification and Audit Agent.

TRIAGE:
{triage_result}

INVESTIGATION:
{investigation_result}

POLICY DECISION:
{policy_result}

REMEDIATION:
{remediation_result}

You MUST call read_sandbox_state.

The incident may be declared RESOLVED only when ALL criteria pass:

- latency <= 30 ms
- packet drop <= 1.0 percent
- authentication failures <= 1.0 percent
- UPF status = HEALTHY

Never assume remediation succeeded.

Produce the final SovereignOps incident report using exactly these sections:

INCIDENT
SEVERITY
ROOT CAUSE
EVIDENCE
POLICY DECISION
ACTIONS EXECUTED
VERIFICATION RESULTS
FINAL STATUS
AUDIT TRAIL

FINAL STATUS must be either:

RESOLVED

or

NOT RESOLVED

Clearly state that all remediation occurred in a synthetic sandbox
and not against production infrastructure.
""",
)


# ---------------------------------------------------------------------
# WORKFLOW ORCHESTRATOR
# ---------------------------------------------------------------------

root_agent = SequentialAgent(
    name="sovereignops_workflow",
    description=(
        "Deterministic governed incident-response workflow for enterprise "
        "and private 5G infrastructure."
    ),
    sub_agents=[
        triage_agent,
        investigation_agent,
        security_policy_agent,
        remediation_agent,
        verification_agent,
    ],
)


app = App(
    root_agent=root_agent,
    name="app",
)
