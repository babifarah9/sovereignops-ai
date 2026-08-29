# Three-minute demo script

Use one fresh event ID during the recording. Do not rehearse with the same ID;
completed IDs are intentionally deduplicated.

## 0:00–0:20 — The problem

**Show:** title card followed by the initial Firestore incident state.

**Say:**

> Critical private 5G incidents demand a fast response, but unrestricted AI
> remediation is too risky. SovereignOps AI combines agent reasoning with a
> deterministic, auditable governance chain.

Point out the synthetic incident's 184 ms latency, 16.4% packet loss, 23.7%
authentication failures, and degraded UPF.

## 0:20–0:45 — The architecture

**Show:** the Mermaid diagram in `ARCHITECTURE.md`.

**Say:**

> Pub/Sub delivers the incident to an authenticated Cloud Run service. A
> transactional Firestore receipt prevents duplicate work. ADK then enforces
> triage, investigation, policy, remediation, and verification in that exact
> order. Every stage is audited, and failed deliveries have a dead-letter path.

## 0:45–1:10 — Prove it is deployed

**Show:** Cloud Run service details with `sovereignops-ai`, region `us-east1`,
revision `sovereignops-ai-00010-x4p`, and 100% traffic. Also show zero minimum
instances and maximum two instances.

**Say:**

> This is the live Google Cloud deployment. It scales to zero and is capped at
> two instances to keep the prototype within a small credit budget.

## 1:10–1:30 — Trigger one incident

Before recording, replace `EVT-DEMO-REPLACE-ME` with a fresh value such as a
timestamped ID.

```bash
gcloud pubsub topics publish incident-events \
  --project sovereignops-agentic-2026 \
  --message='{"event_id":"EVT-DEMO-REPLACE-ME","incident_id":"INC-5G-001","source":"private-5g-monitor"}'
```

**Say:**

> I am publishing one synthetic incident, not calling the agent directly. This
> exercises the same asynchronous delivery path the deployed service uses.

Wait for the publish command to return a message ID. Avoid repeated clicks or
publishes while the workflow is running.

## 1:30–2:15 — Show governed action and evidence

**Show:** Cloud Run logs or Cloud Trace, then the Firestore incident document
and latest audit events.

**Say:**

> The fixed workflow investigated the incident, applied its security policy,
> isolated the suspicious source, and rolled back the unstable UPF policy in a
> sandbox. Verification—not the remediation agent—decides whether the incident
> is resolved.

Point out the final state: 24 ms latency, 0.8% packet loss, 0.6% authentication
failures, healthy UPF, stable policy version, source isolated, and `RESOLVED`.

If showing Trace, highlight the stage hierarchy. Do not open panels that reveal
tokens, credentials, or unrelated project data.

## 2:15–2:35 — Demonstrate safety and reliability

**Show:** both evaluation result pages and the Pub/Sub subscription settings.

**Say:**

> The core recovery case and a safety holdout both score 1.0000 on our
> deterministic compliance metric. Duplicate deliveries are suppressed, and a
> message that fails five times is routed to a dead-letter topic.

## 2:35–3:00 — Close

**Show:** architecture plus before/after metrics.

**Say:**

> SovereignOps AI demonstrates that operational agents can be useful without
> becoming unconstrained. The result is an asynchronous, observable, and
> auditable incident-response prototype built on Google Cloud and ADK.

End with `[Add repository URL]` and `[Add demo/project URL]`.

## Recording safeguards

- Publish only one fresh demo event to limit model and infrastructure usage.
- Keep the Cloud Run endpoint authenticated.
- Confirm the service still has zero minimum and two maximum instances.
- Use a private/incognito window or crop account emails and billing details.
- Record the successful path first; capture optional duplicate/DLQ proof separately.
- Do not imply that the sandbox changed a production telecom network.
