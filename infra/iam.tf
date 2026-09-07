# Two roles per App Runner service:
#  - access role: lets App Runner pull from ECR.
#  - instance role: the running task's permissions (S3, SES, Textract, Secrets, KMS).

data "aws_iam_policy_document" "apprunner_build_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "apprunner_tasks_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["tasks.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_access" {
  name               = "${var.project}-apprunner-access"
  assume_role_policy = data.aws_iam_policy_document.apprunner_build_assume.json
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr" {
  role       = aws_iam_role.apprunner_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_iam_role" "backend_task" {
  name               = "${var.project}-backend-task"
  assume_role_policy = data.aws_iam_policy_document.apprunner_tasks_assume.json
}

data "aws_iam_policy_document" "backend_perms" {
  statement {
    sid     = "S3PhiBuckets"
    actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
    resources = [
      aws_s3_bucket.uploads.arn, "${aws_s3_bucket.uploads.arn}/*",
      aws_s3_bucket.reports.arn, "${aws_s3_bucket.reports.arn}/*",
    ]
  }
  statement {
    sid       = "Secrets"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.app.arn]
  }
  statement {
    sid       = "Kms"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [aws_kms_key.main.arn]
  }
  statement {
    sid       = "Email"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
  }
  statement {
    sid       = "Ocr"
    actions   = ["textract:AnalyzeDocument"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "backend_perms" {
  name   = "${var.project}-backend-perms"
  role   = aws_iam_role.backend_task.id
  policy = data.aws_iam_policy_document.backend_perms.json
}
