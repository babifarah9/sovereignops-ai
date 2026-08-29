# Authenticated incident ingestion with bounded retries and dead-letter retention.

resource "google_service_account" "pubsub_invoker" {
  account_id   = "sovereignops-pubsub-invoker"
  display_name = "SovereignOps Pub/Sub Cloud Run invoker"
  project      = var.project_id

  depends_on = [resource.google_project_service.services]
}

resource "google_cloud_run_v2_service_iam_member" "pubsub_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}

resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.pubsub_invoker.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_topic" "incident_events" {
  name    = var.incident_topic_name
  project = var.project_id

  depends_on = [resource.google_project_service.services]
}

resource "google_pubsub_topic" "incident_events_dead_letter" {
  name    = "${var.incident_topic_name}-dead-letter"
  project = var.project_id

  depends_on = [resource.google_project_service.services]
}

resource "google_pubsub_subscription" "incident_events" {
  name    = var.incident_subscription_name
  project = var.project_id
  topic   = google_pubsub_topic.incident_events.id

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.app.uri}/apps/${var.agent_app_name}/trigger/pubsub"

    oidc_token {
      service_account_email = google_service_account.pubsub_invoker.email
      audience              = google_cloud_run_v2_service.app.uri
    }
  }

  ack_deadline_seconds = 600

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.incident_events_dead_letter.id
    max_delivery_attempts = 5
  }

  expiration_policy {
    ttl = ""
  }
}

resource "google_pubsub_subscription" "incident_events_dead_letter_inspect" {
  name    = "${var.incident_topic_name}-dead-letter-inspect"
  project = var.project_id
  topic   = google_pubsub_topic.incident_events_dead_letter.id

  expiration_policy {
    ttl = ""
  }
}

resource "google_pubsub_topic_iam_member" "dead_letter_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.incident_events_dead_letter.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "dead_letter_forwarder" {
  project      = var.project_id
  subscription = google_pubsub_subscription.incident_events.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
