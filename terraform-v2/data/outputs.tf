output "vpc_id" {
  value = module.data_vpc.vpc_id
}

output "vpc_cidr" {
  value = var.data_vpc_cidr
}

output "private_subnet_ids" {
  value = module.data_vpc.private_subnets
}

output "private_route_table_ids" {
  value = module.data_vpc.private_route_table_ids
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "app_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "app_secret_name" {
  value = aws_secretsmanager_secret.app.name
}

output "pod_role_arn" {
  value = aws_iam_role.pod.arn
}

output "storage_bucket_name" {
  value = aws_s3_bucket.storage.bucket
}

output "frontend_bucket_name" {
  value = aws_s3_bucket.frontend.bucket
}

output "frontend_cloudfront_domain" {
  value = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_api_base_url" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "ecr_auth_repository_url" {
  value = aws_ecr_repository.auth.repository_url
}

output "ecr_storage_repository_url" {
  value = aws_ecr_repository.storage.repository_url
}
