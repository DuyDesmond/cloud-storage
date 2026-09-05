module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.15"

  cluster_name    = "${var.project_name}-${var.environment}-cluster"
  cluster_version = "1.28"

  cluster_endpoint_public_access  = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_group_defaults = {
    ami_type = "AL2_x86_64"
  }

  eks_managed_node_groups = {
    one = {
      name = "node-group-1"
      instance_types = ["t3.medium"]
      min_size     = 1
      max_size     = 3
      desired_size = 2
    }
  }
}
