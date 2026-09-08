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

variable "github_actions_role_name" {
  description = "Existing IAM role assumed by the GitHub Actions CD workflows."
  type        = string
  default     = "nephos-terraform"
}

variable "compute_vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "data_state_path" {
  description = "Path to the applied data stack state file."
  type        = string
  default     = "../data/terraform.tfstate"
}

variable "eks_cluster_version" {
  type    = string
  default = "1.35"
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_desired_size" {
  type    = number
  default = 4
}

variable "node_max_size" {
  type    = number
  default = 10
}
