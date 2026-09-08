terraform {
  required_version = ">= 1.5.0"

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
