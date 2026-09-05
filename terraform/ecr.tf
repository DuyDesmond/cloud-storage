resource "aws_ecr_repository" "auth" {
  name                 = "${var.project_name}-${var.environment}-auth-service"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_ecr_repository" "storage" {
  name                 = "${var.project_name}-${var.environment}-storage-service"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_ecr_repository" "api_gateway" {
  name                 = "${var.project_name}-${var.environment}-api-gateway"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}
