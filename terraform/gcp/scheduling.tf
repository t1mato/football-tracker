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
  description     = "Nightly ingest -> transform -> weather -> transform, in order, failing loudly if any step fails."
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

    # oauth_token is for real Google APIs (*.googleapis.com); oidc_token is for
    # third-party/self-hosted endpoints that validate the JWT themselves.
    oauth_token {
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

resource "google_logging_metric" "scheduler_trigger_failed" {
  project = var.project_id
  name    = "scheduler-trigger-failed"
  # Cloud Scheduler logs an AttemptFinished entry for every trigger attempt,
  # ERROR-severity on failure -- confirmed against the real log from this
  # project's own 2026-09-09 oidc_token/401 incident (resource.type
  # "cloud_scheduler_job", severity "ERROR", jsonPayload.status
  # "UNAUTHENTICATED"). This closes PLAN.md's documented blind spot (the
  # FAILED condition below only fires once a Workflow *execution* finishes,
  # so a Scheduler-side auth failure that creates zero executions produces
  # no execution, no metric point, no email) without the same-day detection
  # cost a condition_absent approach would carry: condition_absent's
  # duration caps at 23h30m (confirmed live, 2026-09-17 -- Terraform's
  # `google_monitoring_alert_policy` update was rejected with "Durations
  # longer than 23h30m are not supported"), which is *shorter* than this
  # workflow's ~24h cadence -- any absence duration under 24h fires every
  # single night, since the metric always goes quiet for just under 24h
  # between consecutive healthy finishes. A log-based metric on the
  # Scheduler's own attempt outcome has no such cadence conflict: it fires
  # the moment a bad attempt is logged, not after a day of silence.
  filter = "resource.type=\"cloud_scheduler_job\" AND resource.labels.job_id=\"${google_cloud_scheduler_job.nightly_trigger.name}\" AND severity=\"ERROR\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

resource "google_monitoring_alert_policy" "nightly_pipeline_failed" {
  project      = var.project_id
  display_name = "Nightly pipeline failed or didn't run"
  combiner     = "OR"

  conditions {
    display_name = "nightly-pipeline execution failed"

    condition_threshold {
      # Confirmed against the real metric descriptor: the label is `status` (not
      # `result`, despite the metric's own name), and the value is uppercase "FAILED".
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

  conditions {
    display_name = "nightly-trigger's own invocation attempt failed"

    condition_threshold {
      filter          = "resource.type=\"cloud_scheduler_job\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.scheduler_trigger_failed.name}\""
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
