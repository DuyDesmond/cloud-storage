resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.project_name}-${var.environment}-app-secrets"
  recovery_window_in_days = 0

  lifecycle {
    prevent_destroy = true
  }
}

# Fetch the Secrets Manager secret created automatically by RDS
data "aws_secretsmanager_secret" "rds_secret" {
  arn = aws_db_instance.postgres.master_user_secret[0].secret_arn
}

# Retrieve the secret payload content
data "aws_secretsmanager_secret_version" "rds_secret_version" {
  secret_id = data.aws_secretsmanager_secret.rds_secret.id
}

# Construct your application secrets JSON safely
resource "aws_secretsmanager_secret_version" "app_initial" {
  secret_id = aws_secretsmanager_secret.app.id

  secret_string = jsonencode({
    DATABASE_URL         = "postgresql://${var.db_username}:${urlencode(jsondecode(data.aws_secretsmanager_secret_version.rds_secret_version.secret_string)["password"])}@${aws_db_instance.postgres.endpoint}/${var.project_name}?sslmode=require"
    SECRET_KEY           = "initial-secret-key-change-in-aws-secrets-manager"
    ALGORITHM            = "HS256"
    ACCESS_TOKEN_EXPIRE  = "30"
    REFRESH_TOKEN_EXPIRE = "7"
    STORAGE_QUOTA_BYTES  = "21474836480"
  })
}