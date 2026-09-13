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

resource "google_service_account" "app_runner" {
  project      = var.project_id
  account_id   = "app-runner"
  display_name = "Streamlit app Cloud Run Service runtime identity -- read-only BigQuery access"

  depends_on = [google_project_service.iam]
}

resource "google_project_iam_member" "app_runner_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.app_runner.email}"
}

resource "google_project_iam_member" "app_runner_bq_jobs" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.app_runner.email}"
}

locals {
  pipeline_image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.pipeline.repository_id}/pipeline:${var.image_tag}"
  app_image      = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.pipeline.repository_id}/app:${var.app_image_tag}"
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

  depends_on = [
    google_project_service.run,
    google_secret_manager_secret_iam_member.pipeline_runner_secret_access,
  ]
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

resource "google_cloud_run_v2_job" "weather" {
  name     = "weather"
  project  = var.project_id
  location = var.region

  template {
    template {
      service_account = google_service_account.pipeline_runner.email
      # Cloud Run Jobs' 600s default was measured live to be too short for the
      # first-ever BigQuery weather run: run_weather() buffers everything
      # (Open-Meteo calls, rate-limited) before dlt's load stage ever writes a
      # row, so a timeout kill mid-run discards the whole attempt, not just
      # the slow part -- confirmed live by two successive 600s-timeout kills
      # that both left raw.match_weather nonexistent in BigQuery. 3600s covers
      # a full current-season backlog with margin; nightly incremental runs
      # will finish in a small fraction of it.
      timeout = "3600s"

      containers {
        image = local.pipeline_image
        args  = ["weather"]

        env {
          name  = "PIPELINE_DESTINATION"
          value = "bigquery"
        }
        env {
          name  = "GCP_PROJECT"
          value = var.project_id
        }
      }
    }
  }

  depends_on = [google_project_service.run]
}

resource "google_cloud_run_v2_service" "app" {
  name     = "app"
  project  = var.project_id
  location = var.region
  # Explicit, not left at the provider default (which happens to match) --
  # "reachable from the public internet" is the single most load-bearing
  # decision this resource makes and shouldn't be implied.
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.app_runner.email

    # Streamlit keeps per-session UI state (selected competition, filters,
    # etc.) in the specific server process a browser's websocket first
    # connected to. With max_instance_count > 1, a reconnect (network blip,
    # backgrounded tab) that lands on the *other* instance has no memory of
    # that session -- session_affinity keeps a browser pinned to the same
    # instance across reconnects.
    session_affinity = true

    # Cloud Run's request timeout defaults to 300s and applies to long-lived
    # connections, including the websocket Streamlit uses for live UI
    # updates. Without raising it, a dashboard tab left open past 5 minutes
    # gets its websocket closed by the platform (Streamlit reconnects, but
    # the user sees a visible interruption).
    timeout = "3600s"

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = local.app_image

      resources {
        limits = {
          # Cloud Run's default (512MiB) is tight for streamlit + pandas +
          # pyarrow resident in memory; cheap insurance against an opaque
          # 500 under real concurrency.
          memory = "1Gi"
        }
      }

      env {
        name  = "APP_DESTINATION"
        value = "bigquery"
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
    }
  }

  depends_on = [google_project_service.run]
}

resource "google_cloud_run_v2_service_iam_member" "app_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
