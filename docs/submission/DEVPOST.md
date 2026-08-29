# SovereignOps AI

**Tagline:** Deterministic, auditable incident response for sovereign private 5G infrastructure.

> Submission fields still needed: [Add hackathon name], [Add repository URL],
> [Add demo video URL], and [Add team members].

## Inspiration

Private 5G networks support infrastructure where an incorrect autonomous action
can be more damaging than the original incident. Operators need the speed of AI
without giving up policy control, traceability, or human accountability.

SovereignOps AI explores a practical middle ground: AI agents perform analysis,
but a deterministic workflow controls which stage runs next, which actions are
allowed, and whether the incident can be declared resolved.

## What it does

SovereignOps AI receives a synthetic private 5G incident asynchronously and
runs it through a fixed governance chain:

1. Triage classifies severity and scope.
2. Investigation identifies likely causes.
3. Security policy evaluates the proposed response.
4. Remediation selects only sandboxed, allowlisted actions.
5. Verification checks the resulting telemetry before closure.

Every stage writes durable incident and audit records. Duplicate Pub/Sub
deliveries are suppressed with transactional Firestore receipts, and repeated
delivery failures are routed to a dead-letter topic for inspection.

For the implemented `INC-5G-001` scenario, the synthetic starting state is:

- latency: 184 ms
- packet loss: 16.4%
- authentication failures: 23.7%
- UPF health: degraded

The governed workflow isolates the suspicious source and rolls the UPF policy
back from `2026.08.20-rc2` to `2026.08.13-stable`. Verification records:

- latency: 24 ms
- packet loss: 0.8%
- authentication failures: 0.6%
- UPF health: healthy
- final status: `RESOLVED`

All remediation is simulated in a sandbox; the prototype does not change a
real telecom network.

## How we built it

- Google Agent Development Kit (ADK) `SequentialAgent` preserves the fixed
  triage-to-verification order.
- Gemini 3.5 Flash Lite on Vertex AI provides reasoning inside the governed stages.
- Cloud Run hosts the authenticated service in `us-east1`.
- Pub/Sub provides asynchronous incident ingestion, retries, and dead-lettering.
- Firestore stores incident state, immutable audit events, and idempotency receipts.
- Cloud Trace and Cloud Logging expose the execution path without capturing
  prompt or response content.
- Deterministic evaluation datasets test both successful remediation and the
  safety holdout path without extra judge-model calls.

## What makes it different

SovereignOps AI is not a free-form chatbot with infrastructure access. Its
governance is part of the execution architecture. Policy cannot be skipped,
verification is required before resolution, remediation tools are allowlisted,
and every material decision is persisted for later review.

The system also treats event delivery as an operational concern: Pub/Sub may
deliver a message more than once, so the workflow claims a stable event key in
a Firestore transaction before invoking the agent. This avoids duplicate model
usage and repeated remediation.

## Challenges we ran into

- Preserving deterministic orchestration while still using agents for reasoning.
- Making at-least-once event delivery safe and cost-conscious.
- Producing durable evidence across Pub/Sub, Cloud Run, ADK, and Firestore.
- Keeping observability useful while disabling message-content capture.
- Building repeatable evaluations for both recovery and safety behavior.

## Accomplishments

- Deployed an authenticated, scale-to-zero Cloud Run service.
- Connected Pub/Sub ingestion to the ADK workflow.
- Added transactional duplicate suppression and a dead-letter path.
- Persisted before/after telemetry, actions, status, and audit history in Firestore.
- Verified the core incident and safety holdout datasets at `1.0000` on the
  deterministic compliance metric.
- Passed the project lint/type/format checks and all 11 unit tests.

## What we learned

Reliable agentic operations depend as much on boundaries as intelligence.
Deterministic sequencing, idempotency, verification, auditability, and privacy
controls make the AI component easier to trust and easier to demonstrate.

## What's next

- Add more synthetic failure modes and adversarial safety cases.
- Add an operator approval gate for higher-impact remediation.
- Build a compact incident timeline dashboard over the Firestore audit trail.
- Add service-level alerts for dead-letter messages and failed verification.
- Validate the architecture in a controlled telecom lab before considering any
  integration with real infrastructure.

## Current deployment evidence

- Google Cloud project: `sovereignops-agentic-2026`
- Cloud Run service: `sovereignops-ai`
- Region: `us-east1`
- Verified revision: `sovereignops-ai-00010-x4p` with 100% traffic
- Scale controls: zero minimum instances, two maximum instances, CPU throttling enabled
- Live endpoint: `https://sovereignops-ai-mbf7xnhejq-ue.a.run.app`
