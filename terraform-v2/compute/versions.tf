terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket       = "nephos-tfstate-662904411478"
    key          = "compute/terraform.tfstate"
    region       = "ap-southeast-1"
    use_lockfile = true
    encrypt      = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.11"
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
      Stack       = "compute"
    }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "terraform_remote_state" "data" {
  backend = "s3"

  config = {
    bucket = "nephos-tfstate-662904411478"
    key    = "data/terraform.tfstate"
    region = "ap-southeast-1"
  }
}
