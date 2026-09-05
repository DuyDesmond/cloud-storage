output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "eks_cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = module.eks.cluster_name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "frontend_cloudfront_url" {
  description = "URL of the CloudFront distribution for the frontend"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "ecr_repository_auth" {
  description = "ECR Repository URL for Auth Service"
  value       = aws_ecr_repository.auth.repository_url
}

output "ecr_repository_storage" {
  description = "ECR Repository URL for Storage Service"
  value       = aws_ecr_repository.storage.repository_url
}

output "ecr_repository_api_gateway" {
  description = "ECR Repository URL for API Gateway"
  value       = aws_ecr_repository.api_gateway.repository_url
}
