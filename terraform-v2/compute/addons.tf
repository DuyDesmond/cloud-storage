module "eks_blueprints_addons" {
  source  = "aws-ia/eks-blueprints-addons/aws"
  version = "~> 1.16"

  cluster_name      = module.eks.cluster_name
  cluster_endpoint  = module.eks.cluster_endpoint
  cluster_version   = module.eks.cluster_version
  oidc_provider_arn = module.eks.oidc_provider_arn

  enable_aws_load_balancer_controller          = true
  enable_secrets_store_csi_driver              = true
  enable_secrets_store_csi_driver_provider_aws = true

  # ADD THIS BLOCK: Configures the base CSI driver to include tokenRequests
  secrets_store_csi_driver = {
    values = [yamlencode({
      syncSecret = {
        enabled = true
      }
      tokenRequests = [
        {
          audience = "sts.amazonaws.com"
        },
        {
          audience = "pods.eks.amazonaws.com"
        }
      ]
    })]
  }

  secrets_store_csi_driver_provider_aws = {
    chart_version = "3.1.3"
    values = [yamlencode({
      secrets-store-csi-driver = {
        install = false
      }
    })]
  }

  helm_releases = {
    ingress-nginx = {
      description      = "A Helm chart to deploy ingress-nginx"
      namespace        = "ingress-nginx"
      create_namespace = true
      name             = "ingress-nginx"
      chart            = "ingress-nginx"
      repository       = "https://kubernetes.github.io/ingress-nginx"
      version          = "4.10.0"
      
      values = [
        yamlencode({
          controller = {
            service = {
              type = "NodePort"
            }
          }
        })
      ]
    }
    aws-for-fluent-bit = {
      description      = "A Helm chart to deploy aws-for-fluent-bit"
      namespace        = "kube-system"
      name             = "aws-for-fluent-bit"
      chart            = "aws-for-fluent-bit"
      repository       = "https://aws.github.io/eks-charts"
      version          = "0.1.32"
      
      values = [
        yamlencode({
          cloudWatch = {
            enabled = true
            region  = var.aws_region
            logGroupName = "/aws/eks/${module.eks.cluster_name}/application"
          }
          firehose = {
            enabled = false
          }
          kinesis = {
            enabled = false
          }
          elasticsearch = {
            enabled = false
          }
        })
      ]
    }
  }
}

provider "helm" {
  kubernetes = {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    exec = {
      api_version = "client.authentication.k8s.io/v1beta1"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.aws_region]
      command     = "aws"
    }
  }
}
