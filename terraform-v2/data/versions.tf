terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket       = "nephos-tfstate-662904411478"
    key          = "data/terraform.tfstate"
    region       = "ap-southeast-1"
    use_lockfile = true
    encrypt      = true
  }

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Nephos"
      Environment = var.environment
      ManagedBy   = "Terraform-v2"
      Stack       = "data"
    }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_iam_role" "github_actions" {
  for_each = toset(var.github_actions_role_names)
  name     = each.value
}
