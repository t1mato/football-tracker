variable "project_id" {
  type        = string
  description = "GCP project ID."
}

variable "region" {
  type        = string
  description = "Region for Cloud Run Jobs and Artifact Registry."
  default     = "us-central1"
}

variable "image_tag" {
  type        = string
  description = "Git short SHA of the pipeline image to deploy. No default -- every apply must say explicitly which image it's shipping."
}
