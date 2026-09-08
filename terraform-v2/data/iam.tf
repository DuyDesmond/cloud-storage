# -----------------------------------------------------------------------------
# Pod Roles (EKS Pod Identity)
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "pod_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole", "sts:TagSession"]
  }
}

# 1. Shared Pod Role (for backward compatibility with nephos-sa)
resource "aws_iam_role" "pod" {
  name               = "${var.project_name}-${var.environment}-pod-role"
  assume_role_policy = data.aws_iam_policy_document.pod_assume_role.json
}

data "aws_iam_policy_document" "pod_data_access" {
  # S3 Bucket-level permissions
  statement {
    sid = "S3BucketAccess"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:ListBucketMultipartUploads"
    ]
    resources = [aws_s3_bucket.storage.arn]
  }

  # S3 Object-level permissions
  statement {
    sid = "S3ObjectAccess"
    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts"
    ]
    resources = ["${aws_s3_bucket.storage.arn}/*"]
  }

  # Secrets Manager permissions (matches exact ARN, suffix wildcard, and name wildcard)
  statement {
    sid = "SecretsManagerAccess"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      aws_secretsmanager_secret.app.arn,
      "${aws_secretsmanager_secret.app.arn}*",
      "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}-${var.environment}-app-secrets*",
      aws_db_instance.postgres.master_user_secret[0].secret_arn,
      "${aws_db_instance.postgres.master_user_secret[0].secret_arn}*"
    ]
  }

  # KMS Decrypt for Secrets Manager
  statement {
    sid = "KMSDecryptViaSecretsManager"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.aws_region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "pod_data_access" {
  name   = "${var.project_name}-${var.environment}-pod-data-access"
  role   = aws_iam_role.pod.id
  policy = data.aws_iam_policy_document.pod_data_access.json
}

# 2. Dedicated Auth Service Pod Role (SEC03 Least Privilege: Secrets Manager only, NO S3)
resource "aws_iam_role" "auth_pod" {
  name               = "${var.project_name}-${var.environment}-auth-pod-role"
  assume_role_policy = data.aws_iam_policy_document.pod_assume_role.json
}

data "aws_iam_policy_document" "auth_pod_access" {
  statement {
    sid = "AuthSecretsManagerAccess"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      aws_secretsmanager_secret.app.arn,
      "${aws_secretsmanager_secret.app.arn}*",
      "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}-${var.environment}-app-secrets*",
      aws_db_instance.postgres.master_user_secret[0].secret_arn,
      "${aws_db_instance.postgres.master_user_secret[0].secret_arn}*"
    ]
  }

  statement {
    sid = "AuthKMSDecryptViaSecretsManager"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.aws_region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "auth_pod_access" {
  name   = "${var.project_name}-${var.environment}-auth-pod-access"
  role   = aws_iam_role.auth_pod.id
  policy = data.aws_iam_policy_document.auth_pod_access.json
}

# 3. Dedicated Storage Service Pod Role (SEC03: S3 + Secrets Manager + KMS)
resource "aws_iam_role" "storage_pod" {
  name               = "${var.project_name}-${var.environment}-storage-pod-role"
  assume_role_policy = data.aws_iam_policy_document.pod_assume_role.json
}

resource "aws_iam_role_policy" "storage_pod_access" {
  name   = "${var.project_name}-${var.environment}-storage-pod-access"
  role   = aws_iam_role.storage_pod.id
  policy = data.aws_iam_policy_document.pod_data_access.json
}

# -----------------------------------------------------------------------------
# Lambda Execution Role (Trash Purge)
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

data "aws_iam_policy_document" "lambda_data_access" {
  # S3 Object & Bucket deletion for expired trashed items
  statement {
    sid = "S3TrashPurgeAccess"
    actions = [
      "s3:DeleteObject",
      "s3:GetObject"
    ]
    resources = ["${aws_s3_bucket.storage.arn}/*"]
  }

  statement {
    sid       = "S3ListBucketAccess"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.storage.arn]
  }

  # Secrets Manager & KMS for DB credentials
  statement {
    sid = "SecretsManagerAccess"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      aws_secretsmanager_secret.app.arn,
      "${aws_secretsmanager_secret.app.arn}*",
      "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}-${var.environment}-app-secrets*",
      aws_db_instance.postgres.master_user_secret[0].secret_arn,
      "${aws_db_instance.postgres.master_user_secret[0].secret_arn}*"
    ]
  }

  statement {
    sid = "KMSDecryptViaSecretsManager"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.aws_region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "lambda_data_access" {
  name   = "${var.project_name}-${var.environment}-lambda-data-access"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_data_access.json
}

# -----------------------------------------------------------------------------
# GitHub Actions Deployment IAM Policy
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "github_actions_cd" {
  # ECR Authentication Token
  statement {
    sid       = "ECRAuthToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # ECR Push/Pull on application repositories
  statement {
    sid = "ECRAppRepositories"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload"
    ]
    resources = [
      aws_ecr_repository.auth.arn,
      aws_ecr_repository.storage.arn
    ]
  }

  # S3 Frontend Bucket Deployment
  statement {
    sid = "S3FrontendDeploy"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.frontend.arn,
      "${aws_s3_bucket.frontend.arn}/*"
    ]
  }

  # CloudFront Invalidation and Distribution Updates
  statement {
    sid = "CloudFrontDeploy"
    actions = [
      "cloudfront:GetDistribution",
      "cloudfront:GetDistributionConfig",
      "cloudfront:UpdateDistribution",
      "cloudfront:CreateInvalidation",
      "cloudfront:GetInvalidation",
      "cloudfront:ListDistributions"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_actions_cd" {
  name   = "${var.project_name}-${var.environment}-github-actions-cd"
  role   = data.aws_iam_role.github_actions.name
  policy = data.aws_iam_policy_document.github_actions_cd.json
}
