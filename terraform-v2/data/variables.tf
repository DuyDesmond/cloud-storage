variable "aws_region" {
  type    = string
  default = "ap-southeast-1"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "project_name" {
  type    = string
  default = "nephos"
}

variable "data_vpc_cidr" {
  type    = string
  default = "10.1.0.0/16"
}

variable "compute_vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "db_username" {
  type    = string
  default = "postgres"
}

variable "api_origin_domain_name" {
  type        = string
  default     = null
  nullable    = true
  description = "ALB DNS name for the optional CloudFront /api/* origin. Set this after the Kubernetes Ingress creates the ALB."
}

variable "github_actions_role_names" {
  description = "Existing IAM roles assumed by the GitHub Actions CD workflows."
  type        = list(string)
  default     = ["ddesmond-cloud-terraform", "nephos-terraform"]
}
