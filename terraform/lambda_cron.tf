data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project_name}-${var.environment}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# The actual source code for this Lambda should be built and pushed separately,
# or we can use a dummy file here that CI/CD overwrites.
# For simplicity, we create a dummy zip and let CI/CD deploy the real code,
# or point to the existing file if running locally.

data "archive_file" "dummy_lambda" {
  type        = "zip"
  output_path = "${path.module}/dummy_lambda.zip"
  source {
    content  = "def handler(event, context):\n  print('dummy')\n"
    filename = "aws_lambda_handler.py"
  }
}

resource "aws_lambda_function" "trash_purge" {
  filename         = data.archive_file.dummy_lambda.output_path
  function_name    = "${var.project_name}-${var.environment}-trash-purge"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "aws_lambda_handler.handler"
  source_code_hash = data.archive_file.dummy_lambda.output_base64sha256
  runtime          = "python3.12"
  timeout          = 300
  
  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    security_group_ids = [aws_security_group.rds.id] # Reusing RDS SG to allow DB access, or create a new one
  }
  
  environment {
    variables = {
      ENVIRONMENT = var.environment
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
