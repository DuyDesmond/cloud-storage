# The RDS master password is automatically managed by Secrets Manager if manage_master_user_password = true
# We can create an additional secret for application-specific config if needed.

resource "aws_secretsmanager_secret" "app_secrets" {
  name = "${var.project_name}-${var.environment}-app-secrets"
}

resource "aws_secretsmanager_secret_version" "app_secrets_initial" {
  secret_id     = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    JWT_SECRET_KEY = "dummy-secret-to-be-replaced-in-aws-console"
  })
}

output "app_secrets_arn" {
  value = aws_secretsmanager_secret.app_secrets.arn
}

# Fetch the automatically created RDS secret ARN
data "aws_secretsmanager_secret" "rds_secret" {
  depends_on = [aws_db_instance.postgres]
  arn        = aws_db_instance.postgres.master_user_secret[0].secret_arn
}

output "rds_secret_arn" {
  value = data.aws_secretsmanager_secret.rds_secret.arn
}
