# Architecture and governance flow

![SovereignOps AI architecture](architecture.png)

The upload-ready PNG is 1600×900. The editable source is `architecture.svg`.

```mermaid
flowchart TD
    Monitor["Synthetic private 5G monitor"] -->|incident event| Topic["Pub/Sub: incident-events"]
    Topic -->|authenticated push| Endpoint["Cloud Run ingestion endpoint"]
    Endpoint --> Claim{"Firestore transaction<br/>claim event key"}
    Claim -->|already complete or active| Ack["Acknowledge duplicate<br/>without model invocation"]
    Claim -->|new claim| Workflow["ADK SequentialAgent"]

    subgraph Governed["Deterministic governance chain"]
        direction LR
        Triage["1. Triage"] --> Investigate["2. Investigation"]
        Investigate --> Policy["3. Security policy"]
        Policy --> Remediate["4. Sandboxed remediation"]
        Remediate --> Verify["5. Verification"]
    end

    Workflow --> Triage
    Verify --> Audit["Firestore<br/>incident + immutable audit events"]
    Audit --> Complete["Mark event receipt complete"]
    Complete --> Response["Acknowledge delivery"]

    Topic -. retry with backoff .-> Endpoint
    Topic -->|after five failed deliveries| DLQ["Pub/Sub dead-letter topic"]
    DLQ --> Inspect["Dead-letter inspection subscription"]

    Endpoint -. telemetry .-> Trace["Cloud Trace + Cloud Logging"]
    Workflow -. stage telemetry .-> Trace
```

## Trust boundaries

- Cloud Run remains authenticated; Pub/Sub invokes it with a dedicated identity.
- Remediation tools mutate only a deterministic sandbox state.
- Policy evaluation always precedes remediation.
- Verification must succeed before the workflow records `RESOLVED`.
- Firestore receipts suppress repeat work under Pub/Sub's at-least-once delivery.
- Prompt and response content capture is disabled in telemetry.
