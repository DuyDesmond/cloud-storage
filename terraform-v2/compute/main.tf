data "aws_caller_identity" "current" {}

data "aws_iam_role" "github_actions" {
  name = var.github_actions_role_name
}
