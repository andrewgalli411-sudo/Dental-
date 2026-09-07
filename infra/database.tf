# RDS Postgres — private only, KMS-encrypted at rest, reachable solely from the
# App Runner VPC connector security group.

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "db" {
  name   = "${var.project}-db-sg"
  vpc_id = aws_vpc.main.id
}

resource "aws_security_group" "apprunner" {
  name   = "${var.project}-apprunner-sg"
  vpc_id = aws_vpc.main.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Only the App Runner connector SG may reach Postgres.
resource "aws_security_group_rule" "db_from_apprunner" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = aws_security_group.apprunner.id
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project}-pg"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  db_name  = "verifi"
  username = var.db_username
  password = var.db_password

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.main.arn

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false # single-AZ for pilot cost; flip on before scale

  backup_retention_period   = 14
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.project}-pg-final"
  # Do not log PHI: keep only error logs, no statement logging.
  apply_immediately = false
}
