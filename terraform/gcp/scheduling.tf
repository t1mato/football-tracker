resource "google_project_service" "workflows" {
  project            = var.project_id
  service            = "workflows.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "workflow_executions" {
  project            = var.project_id
  service            = "workflowexecutions.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_scheduler" {
  project            = var.project_id
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

resource "google_service_account" "pipeline_orchestrator" {
  project      = var.project_id
  account_id   = "pipeline-orchestrator"
  display_name = "Scheduler/Workflows trigger identity -- no BigQuery or secret access"

  depends_on = [google_project_service.iam]
}

resource "google_project_iam_member" "orchestrator_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.pipeline_orchestrator.email}"
}

resource "google_project_iam_member" "orchestrator_workflows_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${google_service_account.pipeline_orchestrator.email}"
}

resource "google_workflows_workflow" "nightly_pipeline" {
  project         = var.project_id
  name            = "nightly-pipeline"
  region          = var.region
  description     = "Nightly ingest -> transform, in order, failing loudly if either step fails."
  service_account = google_service_account.pipeline_orchestrator.id
  source_contents = file("${path.module}/workflows/nightly_pipeline.yaml")

  depends_on = [google_project_service.workflows]
}

resource "google_cloud_scheduler_job" "nightly_trigger" {
  project     = var.project_id
  name        = "nightly-trigger"
  region      = var.region
  description = "Triggers the nightly ingest+transform Cloud Workflow."
  schedule    = "0 2 * * *"
  time_zone   = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/workflows/${google_workflows_workflow.nightly_pipeline.name}/executions"
    headers = {
      "Content-Type" = "application/json"
    }
    body = base64encode(jsonencode({
      argument = jsonencode({})
    }))

    oidc_token {
      service_account_email = google_service_account.pipeline_orchestrator.email
    }
  }

  depends_on = [google_project_service.cloud_scheduler]
}

resource "google_monitoring_notification_channel" "email_alert" {
  project      = var.project_id
  display_name = "Pipeline failure email"
  type         = "email"
  labels = {
    email_address = "tnln3rd@gmail.com"
  }
}

resource "google_monitoring_alert_policy" "nightly_pipeline_failed" {
  project      = var.project_id
  display_name = "Nightly pipeline workflow failed"
  combiner     = "OR"

  conditions {
    display_name = "nightly-pipeline execution failed"

    condition_threshold {
      filter          = "metric.type=\"workflows.googleapis.com/finished_execution_count\" AND resource.type=\"workflows.googleapis.com/Workflow\" AND resource.label.workflow_id=\"${google_workflows_workflow.nightly_pipeline.name}\" AND metric.label.status=\"FAILED\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email_alert.id]
}
