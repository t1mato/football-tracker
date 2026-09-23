# App uptime monitoring -- separate concern from scheduling.tf's pipeline
# alerting: that file watches the nightly ingest/transform/weather jobs,
# this one watches whether the public-facing app itself is reachable.
#
# A request-based signal (Cloud Run's own built-in success/error-rate
# metrics) isn't enough on its own: google_cloud_run_v2_service.app has
# min_instance_count = 0 (main.tf), so real user traffic can go quiet for
# hours at a time, and a request-based SLI has nothing to measure during
# that gap. The uptime check below actively probes on a fixed schedule
# regardless of whether anyone's actually visiting -- it's the only thing
# that gives a continuous signal at this project's traffic level.

resource "google_monitoring_uptime_check_config" "app_health" {
  project      = var.project_id
  display_name = "app /api/health"
  timeout      = "10s"
  period       = "300s"

  # Global spread, not just us-central1 -- a region-local network blip
  # shouldn't read as the app being down.
  selected_regions = ["USA", "EUROPE", "ASIA_PACIFIC"]

  http_check {
    path         = "/api/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = trimprefix(google_cloud_run_v2_service.app.uri, "https://")
    }
  }
}

# A dedicated custom Service (not Cloud Run's own auto-discovered one) --
# required because the SLO below measures the uptime check's own
# check_passed metric, not Cloud Run's built-in request metrics. Same
# min_instance_count = 0 reasoning as the uptime check above.
resource "google_monitoring_custom_service" "app" {
  project      = var.project_id
  service_id   = "football-tracker-app"
  display_name = "football-tracker app"
}

resource "google_monitoring_slo" "app_uptime_99" {
  project      = var.project_id
  service      = google_monitoring_custom_service.app.service_id
  slo_id       = "uptime-99"
  display_name = "99% uptime (30-day rolling), synthetic /api/health probe"

  goal                = 0.99
  rolling_period_days = 30

  windows_based_sli {
    # 5 minutes -- matches the uptime check's own period above, so every
    # check result maps to exactly one window instead of several checks
    # being folded into (or split across) a window.
    window_period = "300s"

    good_bad_metric_filter = join(" AND ", [
      "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
      "resource.type=\"uptime_url\"",
    ])
  }
}

resource "google_monitoring_alert_policy" "app_uptime_failed" {
  project      = var.project_id
  display_name = "App uptime check failing"
  combiner     = "OR"

  conditions {
    display_name = "app_health uptime check failed from >1 region"

    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
        "resource.type=\"uptime_url\"",
      ])
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "60s"

      # The standard Cloud Monitoring shape for an uptime-check alert:
      # count how many of the check's regional checkers reported failure
      # (REDUCE_COUNT_FALSE) in each alignment window, alert once more
      # than 1 region agrees (avoids a single-region network blip paging
      # over a false positive). Not verified against a doc example --
      # verifying this for real against the live API in the apply below,
      # same as everywhere else this project confirms behaviour instead
      # of assuming it.
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.project_id", "resource.label.host"]
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email_alert.id]
}
