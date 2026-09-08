resource "aws_eks_pod_identity_association" "nephos_sa" {
  cluster_name    = module.eks.cluster_name
  namespace       = "nephos"
  service_account = "nephos-sa"
  role_arn        = data.terraform_remote_state.data.outputs.pod_role_arn
}
