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
    JWT_SECRET_KEY = "dummy-secret-to-be-replaced-in-aws-console"
  })
}
