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
