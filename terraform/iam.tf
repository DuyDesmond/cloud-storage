resource "aws_iam_role" "nephos_pod_role" {
  name = "${var.project_name}-${var.environment}-pod-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
      }
    ]
  })
}

# Grant access to S3 for the Storage Service
resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.nephos_pod_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# Grant access to Secrets Manager for the CSI Driver
resource "aws_iam_role_policy_attachment" "secrets_access" {
  role       = aws_iam_role.nephos_pod_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

# Map the IAM role to the Kubernetes ServiceAccount in the nephos namespace
resource "aws_eks_pod_identity_association" "nephos_sa" {
  cluster_name    = module.eks.cluster_name
  namespace       = "nephos"
  service_account = "nephos-sa"
  role_arn        = aws_iam_role.nephos_pod_role.arn
}
