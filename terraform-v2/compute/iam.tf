# Shared service account association (backward compatible with existing nephos-sa deployments)
resource "aws_eks_pod_identity_association" "nephos_sa" {
  cluster_name    = module.eks.cluster_name
  namespace       = "nephos"
  service_account = "nephos-sa"
  role_arn = try(
    data.terraform_remote_state.data.outputs.pod_role_arn,
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-${var.environment}-pod-role"
  )
}

# Dedicated Auth Service Account association (least-privilege: Secrets Manager only)
resource "aws_eks_pod_identity_association" "auth_sa" {
  cluster_name    = module.eks.cluster_name
  namespace       = "nephos"
  service_account = "auth-service-sa"
  role_arn = try(
    data.terraform_remote_state.data.outputs.auth_pod_role_arn,
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-${var.environment}-auth-pod-role"
  )
}

# Dedicated Storage Service Account association (S3 storage + Secrets Manager)
resource "aws_eks_pod_identity_association" "storage_sa" {
  cluster_name    = module.eks.cluster_name
  namespace       = "nephos"
  service_account = "storage-service-sa"
  role_arn = try(
    data.terraform_remote_state.data.outputs.storage_pod_role_arn,
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-${var.environment}-storage-pod-role"
  )
}
