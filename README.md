# SovereignOps AI

SovereignOps AI is a deterministic, auditable incident-response agent for
synthetic private 5G infrastructure. It combines Gemini reasoning with a fixed
Google ADK workflow so that policy review and post-remediation verification
cannot be skipped.

The deployed prototype receives incidents asynchronously through Pub/Sub,
runs a five-stage `SequentialAgent` on Cloud Run, persists incident and audit
records in Firestore, and exports privacy-conscious telemetry to Cloud Trace.
All remediation changes only an in-memory sandbox; it does not touch a real
telecom network.

## Architecture

```text
Synthetic incident
       |
       v
Pub/Sub topic ---- retries ----> dead-letter topic
       |
       v
Authenticated Cloud Run trigger
       |
       +--> Firestore transaction: claim event / suppress duplicates
       |
       v
ADK SequentialAgent
  Triage -> Investigation -> Security Policy -> Remediation -> Verification
       |
       +--> Firestore incident state + immutable audit events
       +--> Cloud Trace and Cloud Logging
```

The detailed diagram and judge-facing material are in the
[submission pack](docs/submission/README.md).

## Required stack

- Python 3.11–3.13
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- [`agents-cli`](https://github.com/GoogleCloudPlatform/agent-starter-pack)
  compatible with the scaffolded `1.4.x` project
- Google Cloud CLI (`gcloud`) for deployment
- A Google Cloud project with billing enabled for the cloud path

The agent model is `gemini-3.5-flash-lite`. Local execution supports either
Vertex AI application credentials or a Gemini API key.

## Local spin-up

### 1. Install dependencies

```bash
git clone https://github.com/babifarah9/sovereignops-ai.git
cd sovereignops-ai
uv sync --all-groups
uv tool install "google-agents-cli~=1.4.0"
```

### 2. Configure authentication

Copy the example without committing the resulting `.env` file:

```bash
cp .env.example .env
```

For Vertex AI, set these values in `.env` and authenticate with Application
Default Credentials:

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
```

```bash
gcloud auth application-default login
```

Alternatively, set `GOOGLE_GENAI_USE_VERTEXAI=false` and provide
`GEMINI_API_KEY` in the local `.env`. Never commit that file or paste a key into
deployment commands, screenshots, logs, or issue reports.

Firestore persistence is optional locally. With valid Google Cloud credentials,
these defaults are used:

```dotenv
FIRESTORE_DATABASE=(default)
FIRESTORE_INCIDENT_COLLECTION=incidents
FIRESTORE_EVENT_RECEIPT_COLLECTION=event_receipts
```

### 3. Run the agent

Quick command-line smoke test:

```bash
agents-cli run "Investigate synthetic incident INC-5G-001."
```

Interactive local playground:

```bash
agents-cli playground
```

The generated FastAPI application can also be started directly:

```bash
uv run uvicorn app.fast_api_app:app --host 127.0.0.1 --port 8000
```

## Test and evaluate

Run deterministic code tests and the full project quality checks:

```bash
uv run pytest tests/unit
agents-cli lint
```

Run the two behavioral evaluation datasets:

```bash
agents-cli eval run \
  --dataset tests/eval/datasets/core-incident.json \
  --config tests/eval/eval_config.yaml
agents-cli eval run \
  --dataset tests/eval/datasets/safety-holdout.json \
  --config tests/eval/eval_config.yaml
```

The repository includes a deterministic `sovereignops_compliance` metric. The
verified core and safety-holdout runs each scored `1.0000` with one valid case
and zero grading errors.

## Google Cloud deployment

The reference deployment uses project `sovereignops-agentic-2026`, region
`us-east1`, and an authenticated Cloud Run service named `sovereignops-ai`.
Substitute your own project ID when reproducing it.

### 1. Select the project and enable APIs

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  cloudtrace.googleapis.com
```

Create the default Firestore database once if the project does not already
have one:

```bash
gcloud firestore databases create \
  --database='(default)' \
  --location=nam5 \
  --type=firestore-native
```

### 2. Choose model authentication

The recommended Cloud Run path uses Vertex AI and the runtime service account,
so no API key is attached to the service:

```bash
MODEL_ENV="GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=global"
```

If you intentionally use the Gemini API instead, store its key in Secret
Manager. Never use a plain Cloud Run environment variable.

#### Optional Gemini API key path

Create a Secret Manager secret from a local, uncommitted value:

```bash
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create sovereignops-gemini-api-key \
  --replication-policy=automatic \
  --data-file=-
```

Grant `roles/secretmanager.secretAccessor` on this secret to the default Cloud
Run runtime service account used by the reference deployment:

```bash
PROJECT_NUMBER="$(gcloud projects describe YOUR_PROJECT_ID \
  --format='value(projectNumber)')"
RUNTIME_SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding sovereignops-gemini-api-key \
  --project YOUR_PROJECT_ID \
  --member="serviceAccount:${RUNTIME_SERVICE_ACCOUNT}" \
  --role=roles/secretmanager.secretAccessor
```

### 3. Deploy with bounded scaling

```bash
agents-cli deploy \
  --project YOUR_PROJECT_ID \
  --region us-east1 \
  --service-name sovereignops-ai \
  --min-instances 0 \
  --max-instances 2 \
  --update-env-vars "$MODEL_ENV"
```

For the optional Gemini API path, replace `--update-env-vars "$MODEL_ENV"`
with `--secrets GEMINI_API_KEY=sovereignops-gemini-api-key:latest`.

The zero minimum and two-instance maximum keep the demonstration deployment
bounded and allow it to scale to zero while idle.

### 4. Configure Pub/Sub and Firestore access

After Cloud Run reports ready, configure authenticated event ingestion:

```bash
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID \
GOOGLE_CLOUD_RUN_REGION=us-east1 \
bash deployment/configure_event_ingestion.sh
```

The helper creates or updates:

- topic `incident-events`
- authenticated push subscription `sovereignops-incident-events`
- dead-letter topic `incident-events-dead-letter`
- inspection subscription `incident-events-dead-letter-inspect`
- Cloud Run invocation, Firestore writer, Cloud Trace, and Pub/Sub service-account permissions

Messages are retried with backoff and move to the dead-letter topic after five
failed deliveries.

### 5. Verify the deployment

```bash
agents-cli deploy --list
agents-cli deploy --status
gcloud run services describe sovereignops-ai \
  --region us-east1 \
  --format='value(status.url,status.latestReadyRevisionName)'
```

Publish exactly one synthetic event with a fresh stable `event_id`:

```bash
gcloud pubsub topics publish incident-events \
  --message='{"event_id":"EVT-DEMO-UNIQUE","incident_id":"INC-5G-001","source":"private-5g-monitor"}'
```

Idempotency uses `event_id`, then `incident_id`, and finally the Pub/Sub message
ID. Completed or concurrently active duplicates are acknowledged without a
second Gemini invocation or repeated remediation.

## Implemented incident result

The synthetic `INC-5G-001` run begins with 184 ms latency, 16.4% packet loss,
23.7% authentication failures, and a degraded UPF. The governed workflow
isolates the suspicious source and rolls back the sandbox policy. Verification
records 24 ms latency, 0.8% packet loss, 0.6% authentication failures, a healthy
UPF, and final status `RESOLVED`.

## Repository map

```text
app/                         ADK workflow, tools, FastAPI app, persistence
deployment/                  Pub/Sub and Cloud Run configuration helper
tests/unit/                  deterministic code tests
tests/eval/datasets/         core and safety-holdout datasets
tests/eval/                  deterministic compliance metric
docs/submission/             Devpost copy, demo script, diagram, checklist
artifacts/grade_results/     verified local evaluation reports
```

## Security and cost controls

- Cloud Run remains authenticated.
- The reference deployment uses Vertex AI service-account authentication; an
  optional Gemini API credential is stored only in Secret Manager.
- Prompt and response content capture is disabled in tracing.
- Remediation is limited to an in-memory deterministic sandbox.
- Firestore transactions suppress duplicate event processing.
- Cloud Run scales to zero and is capped at two instances.
- No load generator or recurring event publisher is required.

## License

SovereignOps AI is available under the [MIT License](LICENSE). Components that
retain an upstream license header remain subject to that license.
