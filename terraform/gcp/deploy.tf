resource "google_service_account" "ci_deployer" {
  project      = var.project_id
  account_id   = "ci-deployer"
  display_name = "GitHub Actions -- push-only identity for the app image"

  depends_on = [google_project_service.iam]
}

resource "google_artifact_registry_repository_iam_member" "ci_deployer_writer" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.pipeline.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.ci_deployer.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github-actions"
  display_name              = "GitHub Actions"

  depends_on = [google_project_service.iam]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # Belt-and-suspenders with the principalSet condition below: even if a
  # future binding were ever added without that scoping, no token from any
  # repo but this one satisfies the provider itself.
  attribute_condition = "assertion.repository == 't1mato/football-tracker'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "ci_deployer_wif_user" {
  service_account_id = google_service_account.ci_deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/t1mato/football-tracker"
}
