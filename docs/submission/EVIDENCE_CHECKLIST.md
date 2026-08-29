# Submission evidence checklist

Capture these items once, then reuse the cleanest images in the demo and project
gallery. Crop account email addresses, billing data, tokens, and unrelated logs.

## Required proof

- [ ] Cloud Run overview showing service `sovereignops-ai`, region `us-east1`,
  revision `sovereignops-ai-00010-x4p`, and 100% traffic.
- [ ] Cloud Run scaling configuration showing zero minimum and two maximum instances.
- [ ] Pub/Sub topic `incident-events` and push subscription
  `sovereignops-incident-events`.
- [ ] Subscription retry policy (10–600 seconds), five delivery attempts, and
  dead-letter topic `incident-events-dead-letter`.
- [ ] Firestore `INC-5G-001` initial telemetry.
- [ ] Firestore `INC-5G-001` final telemetry, actions, and `RESOLVED` status.
- [ ] Firestore audit-event timeline showing the five governed stages.
- [ ] Cloud Trace or structured Cloud Run logs showing one successful execution.
- [ ] Core evaluation result with score `1.0000`, one valid case, zero errors.
- [ ] Safety-holdout result with score `1.0000`, one valid case, zero errors.
- [ ] Terminal result showing 11 passing unit tests and successful lint/type/format checks.

## Local evaluation artifacts

- Core incident:
  `artifacts/grade_results/results_20260829_201308.html`
- Safety holdout:
  `artifacts/grade_results/results_20260829_201355.html`

Open the files locally before recording and confirm that each displays the
expected score. Keep the generated result JSON files with the submission archive
even if only the HTML pages appear in the video.

## Submission fields

- [ ] Project title and tagline
- [ ] Project description copied and reviewed from `DEVPOST.md`
- [ ] Architecture image exported from `ARCHITECTURE.md`
- [ ] Repository URL
- [ ] Demo video URL
- [ ] Team member names and roles
- [ ] Google Cloud products and ADK called out accurately
- [ ] Synthetic/sandbox limitation stated clearly
- [ ] Links tested in a signed-out browser

## Final five-minute check

- [ ] The video is publicly viewable or viewable with the required link setting.
- [ ] The repository contains no secrets or local credential files.
- [ ] The deployed endpoint remains authenticated.
- [ ] No minimum Cloud Run instances are configured.
- [ ] No repeated test publisher or load generator is running.
- [ ] The final submission preview renders every image and link.
