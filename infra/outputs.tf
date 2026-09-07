output "ecr_backend_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "db_endpoint" {
  value     = aws_db_instance.main.address
  sensitive = true
}

output "app_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "backend_url" {
  value       = var.backend_image == "" ? "(set backend_image, then re-apply)" : aws_apprunner_service.backend[0].service_url
  description = "App Runner URL for the FastAPI backend."
}

output "frontend_url" {
  value       = var.frontend_image == "" ? "(set frontend_image, then re-apply)" : aws_apprunner_service.frontend[0].service_url
  description = "App Runner URL for the Next.js app — point app.<domain> here."
}

output "ses_dkim_tokens" {
  value       = var.sending_domain == "" ? [] : aws_ses_domain_dkim.main[0].dkim_tokens
  description = "Add these as CNAME records to verify DKIM."
}
