output "artifact_registry_url" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.pipeline.repository_id}"
  description = "Base URL to push/pull the pipeline image, e.g. <this>/pipeline:<tag>."
}

output "pipeline_runner_email" {
  value       = google_service_account.pipeline_runner.email
  description = "Service account both Cloud Run Jobs run as."
}
