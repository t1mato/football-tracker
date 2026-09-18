output "artifact_registry_url" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.pipeline.repository_id}"
  description = "Base URL to push/pull the pipeline image, e.g. <this>/pipeline:<tag>."
}

output "pipeline_runner_email" {
  value       = google_service_account.pipeline_runner.email
  description = "Service account both Cloud Run Jobs run as."
}

output "secret_id" {
  value       = google_secret_manager_secret.football_data_token.secret_id
  description = "Secret Manager secret ID -- add the real token with `gcloud secrets versions add`."
}

output "ci_deployer_email" {
  value       = google_service_account.ci_deployer.email
  description = "Service account cd.yml impersonates to push the app image."
}

output "workload_identity_provider" {
  value       = google_iam_workload_identity_pool_provider.github.name
  description = "Full resource name for cd.yml's google-github-actions/auth workload_identity_provider input."
}
