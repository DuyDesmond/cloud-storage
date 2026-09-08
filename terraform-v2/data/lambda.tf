resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-${var.environment}-data-lambda-sg"
  description = "Lambda access to data VPC resources"
  vpc_id      = module.data_vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "rds_from_lambda" {
  type                     = "ingress"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.lambda.id
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
}

data "archive_file" "dummy_lambda" {
  type        = "zip"
  output_path = "${path.module}/dummy_lambda.zip"

  source {
    content  = "def handler(event, context):\n    print('dummy')\n"
    filename = "aws_lambda_handler.py"
  }
}

resource "aws_lambda_function" "trash_purge" {
  filename         = data.archive_file.dummy_lambda.output_path
  function_name    = "${var.project_name}-${var.environment}-trash-purge"
  role             = aws_iam_role.lambda.arn
  handler          = "aws_lambda_handler.handler"
  source_code_hash = data.archive_file.dummy_lambda.output_base64sha256
  runtime          = "python3.12"
  timeout          = 300

  vpc_config {
    subnet_ids         = module.data_vpc.private_subnets
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      BUCKET_NAME          = aws_s3_bucket.storage.bucket
      BUCKET_REGION_NAME   = var.aws_region
      DATABASE_URL         = "postgresql://${var.db_username}@${aws_db_instance.postgres.endpoint}/${var.project_name}"
      API_STR              = "/api/v2"
      STORAGE_QUOTA_BYTES  = "21474836480"
      SECRET_KEY           = "lambda-internal-placeholder-051004"
      ALGORITHM            = "HS256"
      ACCESS_TOKEN_EXPIRE  = "30"
      REFRESH_TOKEN_EXPIRE = "7"
      SECRET_NAME          = aws_secretsmanager_secret.app.name
    }
  }
}

resource "aws_cloudwatch_event_rule" "daily_purge" {
  name                = "${var.project_name}-${var.environment}-daily-purge"
  description         = "Triggers the trash purge Lambda every day at midnight"
  schedule_expression = "cron(0 0 * * ? *)"
}

resource "aws_cloudwatch_event_target" "trigger_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_purge.name
  target_id = "TrashPurgeLambda"
  arn       = aws_lambda_function.trash_purge.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trash_purge.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_purge.arn
}
