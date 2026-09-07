# KMS customer-managed key encrypts RDS, S3, and Secrets Manager. One key keeps
# the audit surface small; rotate annually.

resource "aws_kms_key" "main" {
  description             = "${var.project} PHI encryption key"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.project}-phi"
  target_key_id = aws_kms_key.main.key_id
}

# App configuration + secrets, injected into the app at runtime (never in code).
resource "aws_secretsmanager_secret" "app" {
  name       = "${var.project}/app"
  kms_key_id = aws_kms_key.main.arn
}

resource "random_password" "session_secret" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DATABASE_URL      = "postgresql+psycopg://${var.db_username}:${var.db_password}@${aws_db_instance.main.address}:5432/${aws_db_instance.main.db_name}"
    SESSION_SECRET    = random_password.session_secret.result
    ENVIRONMENT       = "prod"
    AWS_REGION        = var.aws_region
    S3_BUCKET_UPLOADS = aws_s3_bucket.uploads.bucket
    S3_BUCKET_REPORTS = aws_s3_bucket.reports.bucket
    COOKIE_SECURE     = "true"
    PUBLIC_BASE_URL   = var.app_public_url
  })
}
