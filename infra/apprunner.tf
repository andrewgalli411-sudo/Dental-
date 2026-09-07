# App Runner runs both services from ECR images. The backend joins the VPC (to
# reach RDS privately); the frontend stays managed-egress (it only calls the
# backend over HTTPS). Set backend_image / frontend_image after the first push.

resource "aws_apprunner_vpc_connector" "main" {
  vpc_connector_name = "${var.project}-connector"
  subnets            = aws_subnet.private[*].id
  security_groups    = [aws_security_group.apprunner.id]
}

resource "aws_apprunner_service" "backend" {
  count        = var.backend_image == "" ? 0 : 1
  service_name = "${var.project}-backend"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access.arn
    }
    image_repository {
      image_identifier      = var.backend_image
      image_repository_type = "ECR"
      image_configuration {
        port = "8000"
        # Secrets are read from Secrets Manager by the app at boot using this ARN.
        runtime_environment_variables = {
          APP_SECRET_ARN = aws_secretsmanager_secret.app.arn
        }
      }
    }
    auto_deployments_enabled = false
  }

  instance_configuration {
    cpu               = "1024"
    memory            = "2048"
    instance_role_arn = aws_iam_role.backend_task.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.main.arn
    }
  }

  health_check_configuration {
    protocol = "HTTP"
    path     = "/healthz"
  }
}

resource "aws_apprunner_service" "frontend" {
  count        = var.frontend_image == "" ? 0 : 1
  service_name = "${var.project}-frontend"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access.arn
    }
    image_repository {
      image_identifier      = var.frontend_image
      image_repository_type = "ECR"
      image_configuration {
        port = "3000"
        runtime_environment_variables = {
          # The Next server proxies /api/* here (same-origin cookie). Prefer the
          # backend's private/internal URL once you front both with one domain.
          BACKEND_URL = var.backend_image == "" ? "" : aws_apprunner_service.backend[0].service_url
        }
      }
    }
    auto_deployments_enabled = false
  }

  instance_configuration {
    cpu    = "512"
    memory = "1024"
  }
}
