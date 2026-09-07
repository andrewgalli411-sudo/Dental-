# Scheduled PHI purge: once a day, run `python -m scripts.purge_phi` as a Fargate
# task using the backend image. Enforces the 7-day retention promise without a
# long-running service. Created only once the backend image exists.

locals {
  purge_enabled = var.backend_image == "" ? 0 : 1
}

resource "aws_ecs_cluster" "jobs" {
  count = local.purge_enabled
  name  = "${var.project}-jobs"
}

resource "aws_cloudwatch_log_group" "purge" {
  count             = local.purge_enabled
  name              = "/ecs/${var.project}-purge"
  retention_in_days = 30
}

# Execution role: pull the image, write logs, and read the secret for valueFrom.
data "aws_iam_policy_document" "ecs_exec_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_exec" {
  count              = local.purge_enabled
  name               = "${var.project}-ecs-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_exec_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_exec_base" {
  count      = local.purge_enabled
  role       = aws_iam_role.ecs_exec[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_exec_secrets" {
  count = local.purge_enabled
  name  = "${var.project}-ecs-exec-secrets"
  role  = aws_iam_role.ecs_exec[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.app.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.main.arn]
      },
    ]
  })
}

resource "aws_ecs_task_definition" "purge" {
  count                    = local.purge_enabled
  family                   = "${var.project}-purge"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_exec[0].arn
  task_role_arn            = aws_iam_role.backend_task.arn # has S3/KMS/secrets perms

  container_definitions = jsonencode([
    {
      name    = "purge"
      image   = var.backend_image
      command = ["python", "-m", "scripts.purge_phi"]
      # Inject config from the secret's JSON keys directly (no entrypoint hack).
      secrets = [
        { name = "DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.app.arn}:DATABASE_URL::" },
        { name = "S3_BUCKET_UPLOADS", valueFrom = "${aws_secretsmanager_secret.app.arn}:S3_BUCKET_UPLOADS::" },
        { name = "S3_BUCKET_REPORTS", valueFrom = "${aws_secretsmanager_secret.app.arn}:S3_BUCKET_REPORTS::" },
        { name = "AWS_REGION", valueFrom = "${aws_secretsmanager_secret.app.arn}:AWS_REGION::" },
        { name = "ENVIRONMENT", valueFrom = "${aws_secretsmanager_secret.app.arn}:ENVIRONMENT::" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.purge[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "purge"
        }
      }
    }
  ])
}

# Role that EventBridge Scheduler assumes to launch the task.
data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  count              = local.purge_enabled
  name               = "${var.project}-purge-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

resource "aws_iam_role_policy" "scheduler" {
  count = local.purge_enabled
  name  = "${var.project}-purge-scheduler"
  role  = aws_iam_role.scheduler[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ecs:RunTask"], Resource = ["*"] },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.ecs_exec[0].arn, aws_iam_role.backend_task.arn]
      },
    ]
  })
}

resource "aws_scheduler_schedule" "purge" {
  count = local.purge_enabled
  name  = "${var.project}-daily-purge"
  flexible_time_window { mode = "OFF" }
  schedule_expression          = "cron(30 8 * * ? *)" # 08:30 UTC daily
  schedule_expression_timezone = "UTC"

  target {
    arn      = aws_ecs_cluster.jobs[0].arn
    role_arn = aws_iam_role.scheduler[0].arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.purge[0].arn
      launch_type         = "FARGATE"
      network_configuration {
        subnets          = aws_subnet.private[*].id
        security_groups  = [aws_security_group.apprunner.id]
        assign_public_ip = false
      }
    }
  }
}
