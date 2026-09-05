module "eks_blueprints_addons" {
  source  = "aws-ia/eks-blueprints-addons/aws"
  version = "~> 1.16"

  cluster_name      = module.eks.cluster_name
  cluster_endpoint  = module.eks.cluster_endpoint
  cluster_version   = module.eks.cluster_version
  oidc_provider_arn = module.eks.oidc_provider_arn

  # AWS Load Balancer Controller for Ingress (ALB)
  enable_aws_load_balancer_controller = true
  
  # Secrets Store CSI Driver and AWS Provider
  enable_secrets_store_csi_driver              = true
  enable_secrets_store_csi_driver_provider_aws = true
}
