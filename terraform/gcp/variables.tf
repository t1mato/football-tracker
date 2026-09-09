variable "project_id" {
  type        = string
  description = "GCP project ID."
}

variable "region" {
  type        = string
  description = "Region for Cloud Run Jobs and Artifact Registry."
  default     = "us-central1"
}
