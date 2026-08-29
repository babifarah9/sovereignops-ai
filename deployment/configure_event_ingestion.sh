#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-sovereignops-agentic-2026}"
REGION="${GOOGLE_CLOUD_RUN_REGION:-us-east1}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-sovereignops-ai}"
TOPIC_NAME="${PUBSUB_TOPIC:-incident-events}"
SUBSCRIPTION_NAME="${PUBSUB_SUBSCRIPTION:-sovereignops-incident-events}"
DEAD_LETTER_TOPIC="${PUBSUB_DEAD_LETTER_TOPIC:-incident-events-dead-letter}"
DEAD_LETTER_SUBSCRIPTION="${PUBSUB_DEAD_LETTER_SUBSCRIPTION:-incident-events-dead-letter-inspect}"
INVOKER_ACCOUNT="${PUBSUB_INVOKER_ACCOUNT:-sovereignops-pubsub-invoker}"

gcloud services enable firestore.googleapis.com pubsub.googleapis.com run.googleapis.com \
  --project "${PROJECT_ID}"

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format='value(status.url)')"
RUNTIME_ACCOUNT="$(gcloud run services describe "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format='value(spec.template.spec.serviceAccountName)')"
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" \
  --format='value(projectNumber)')"

if [[ -z "${RUNTIME_ACCOUNT}" ]]; then
  RUNTIME_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi

INVOKER_EMAIL="${INVOKER_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "${INVOKER_EMAIL}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${INVOKER_ACCOUNT}" \
    --project "${PROJECT_ID}" \
    --display-name "SovereignOps Pub/Sub Cloud Run invoker"
fi

PUBSUB_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
gcloud iam service-accounts add-iam-policy-binding "${INVOKER_EMAIL}" \
  --project "${PROJECT_ID}" \
  --member "serviceAccount:${PUBSUB_SERVICE_AGENT}" \
  --role roles/iam.serviceAccountTokenCreator

gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --member "serviceAccount:${INVOKER_EMAIL}" \
  --role roles/run.invoker

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member "serviceAccount:${RUNTIME_ACCOUNT}" \
  --role roles/datastore.user \
  --condition=None

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member "serviceAccount:${RUNTIME_ACCOUNT}" \
  --role roles/cloudtrace.agent \
  --condition=None

if ! gcloud pubsub topics describe "${TOPIC_NAME}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud pubsub topics create "${TOPIC_NAME}" --project "${PROJECT_ID}"
fi

if ! gcloud pubsub topics describe "${DEAD_LETTER_TOPIC}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud pubsub topics create "${DEAD_LETTER_TOPIC}" --project "${PROJECT_ID}"
fi

if ! gcloud pubsub subscriptions describe "${DEAD_LETTER_SUBSCRIPTION}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud pubsub subscriptions create "${DEAD_LETTER_SUBSCRIPTION}" \
    --project "${PROJECT_ID}" \
    --topic "${DEAD_LETTER_TOPIC}" \
    --expiration-period=never
fi

PUSH_ENDPOINT="${SERVICE_URL}/apps/app/trigger/pubsub"
if gcloud pubsub subscriptions describe "${SUBSCRIPTION_NAME}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud pubsub subscriptions update "${SUBSCRIPTION_NAME}" \
    --project "${PROJECT_ID}" \
    --push-endpoint "${PUSH_ENDPOINT}" \
    --push-auth-service-account "${INVOKER_EMAIL}" \
    --push-auth-token-audience "${SERVICE_URL}" \
    --dead-letter-topic "${DEAD_LETTER_TOPIC}" \
    --max-delivery-attempts 5
else
  gcloud pubsub subscriptions create "${SUBSCRIPTION_NAME}" \
    --project "${PROJECT_ID}" \
    --topic "${TOPIC_NAME}" \
    --push-endpoint "${PUSH_ENDPOINT}" \
    --push-auth-service-account "${INVOKER_EMAIL}" \
    --push-auth-token-audience "${SERVICE_URL}" \
    --ack-deadline 600 \
    --min-retry-delay 10s \
    --max-retry-delay 600s \
    --dead-letter-topic "${DEAD_LETTER_TOPIC}" \
    --max-delivery-attempts 5
fi

gcloud pubsub topics add-iam-policy-binding "${DEAD_LETTER_TOPIC}" \
  --project "${PROJECT_ID}" \
  --member "serviceAccount:${PUBSUB_SERVICE_AGENT}" \
  --role roles/pubsub.publisher

gcloud pubsub subscriptions add-iam-policy-binding "${SUBSCRIPTION_NAME}" \
  --project "${PROJECT_ID}" \
  --member "serviceAccount:${PUBSUB_SERVICE_AGENT}" \
  --role roles/pubsub.subscriber

echo "Pub/Sub pushes ${TOPIC_NAME} to ${PUSH_ENDPOINT}."
echo "Failed events move to ${DEAD_LETTER_TOPIC} after 5 delivery attempts."
echo "Firestore audit writes run as ${RUNTIME_ACCOUNT}."
