terraform {
  required_version = ">= 1.9"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  backend "gcs" {
    bucket = "football-tracker-508022-tfstate"
    prefix = "gcp"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "run" {
  project            = var.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secret_manager" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  project            = var.project_id
  service            = "iam.googleapis.com"
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "pipeline" {
  project       = var.project_id
  location      = var.region
  repository_id = "football-tracker"
  format        = "DOCKER"
  description   = "Ingestion + transform pipeline image for Cloud Run Jobs."

  depends_on = [google_project_service.artifact_registry]
}

resource "google_service_account" "pipeline_runner" {
  project      = var.project_id
  account_id   = "pipeline-runner"
  display_name = "Football pipeline Cloud Run Jobs runtime identity"

  depends_on = [google_project_service.iam]
}

resource "google_project_iam_member" "pipeline_runner_bq_data" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

resource "google_project_iam_member" "pipeline_runner_bq_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

resource "google_secret_manager_secret" "football_data_token" {
  project   = var.project_id
  secret_id = "football-data-api-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secret_manager]
}

resource "google_secret_manager_secret_iam_member" "pipeline_runner_secret_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.football_data_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

locals {
  pipeline_image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.pipeline.repository_id}/pipeline:${var.image_tag}"
}

resource "google_cloud_run_v2_job" "ingest" {
  name     = "ingest"
  project  = var.project_id
  location = var.region

  template {
    template {
      service_account = google_service_account.pipeline_runner.email

      containers {
        image = local.pipeline_image
        args  = ["ingest"]

        env {
          name  = "PIPELINE_DESTINATION"
          value = "bigquery"
        }
        env {
          name  = "GCP_PROJECT"
          value = var.project_id
        }

        volume_mounts {
          name       = "secrets"
          mount_path = "/app/.dlt"
        }
      }

      volumes {
        name = "secrets"
        secret {
          secret = google_secret_manager_secret.football_data_token.secret_id
          items {
            version = "latest"
            path    = "secrets.toml"
          }
        }
      }
    }
  }

  depends_on = [google_project_service.run]
}

resource "google_cloud_run_v2_job" "transform" {
  name     = "transform"
  project  = var.project_id
  location = var.region

  template {
    template {
      service_account = google_service_account.pipeline_runner.email

      containers {
        image = local.pipeline_image
        args  = ["transform"]

        env {
          name  = "GCP_PROJECT"
          value = var.project_id
        }
      }
    }
  }

  depends_on = [google_project_service.run]
}
