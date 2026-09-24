data "aws_caller_identity" "current" {}

data "aws_iam_role" "github_actions" {
  for_each = toset(var.github_actions_role_names)
  name     = each.value
}
