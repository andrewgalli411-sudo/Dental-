variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "verifi"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "db_username" {
  type    = string
  default = "verifi"
}

variable "db_password" {
  type      = string
  sensitive = true
  # Provide via TF_VAR_db_password or a tfvars file kept out of git.
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro" # fine for 1-3 pilots; scale later
}

variable "backend_image" {
  type        = string
  description = "ECR image URI:tag for the FastAPI backend (set after first push)."
  default     = ""
}

variable "frontend_image" {
  type        = string
  description = "ECR image URI:tag for the Next.js app (set after first push)."
  default     = ""
}

variable "sending_domain" {
  type        = string
  description = "Domain SES sends report links from, e.g. verifidental.com."
  default     = ""
}

variable "app_public_url" {
  type        = string
  description = "Public URL the app is served at, e.g. https://app.verifidental.com."
  default     = ""
}
