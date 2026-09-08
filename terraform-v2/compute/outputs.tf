output "vpc_id" {
  value = module.compute_vpc.vpc_id
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "data_vpc_id" {
  value = data.terraform_remote_state.data.outputs.vpc_id
}

output "deployment_order" {
  value = "Apply data first, then compute, then apply the Kubernetes manifests in k8s/."
}
