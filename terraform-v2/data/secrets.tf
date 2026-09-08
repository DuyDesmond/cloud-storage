resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.project_name}-${var.environment}-app-secrets"
  recovery_window_in_days = 0

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_secretsmanager_secret_version" "app_initial" {
  secret_id = aws_secretsmanager_secret.app.id

  secret_string = jsonencode({
    DATABASE_URL         = "postgresql://${var.db_username}@${aws_db_instance.postgres.endpoint}/${var.project_name}"
    SECRET_KEY           = "initial-secret-key-change-in-aws-secrets-manager"
    ALGORITHM            = "HS256"
    ACCESS_TOKEN_EXPIRE  = "30"
    REFRESH_TOKEN_EXPIRE = "7"
    STORAGE_QUOTA_BYTES  = "21474836480"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
