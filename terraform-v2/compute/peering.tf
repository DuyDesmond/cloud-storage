resource "aws_vpc_peering_connection" "compute_to_data" {
  vpc_id      = module.compute_vpc.vpc_id
  peer_vpc_id = data.terraform_remote_state.data.outputs.vpc_id
  auto_accept = true

  tags = {
    Name = "${var.project_name}-${var.environment}-compute-to-data"
  }
}

resource "aws_route" "compute_to_data" {
  count = length(module.compute_vpc.private_route_table_ids)

  route_table_id            = module.compute_vpc.private_route_table_ids[count.index]
  destination_cidr_block    = data.terraform_remote_state.data.outputs.vpc_cidr
  vpc_peering_connection_id = aws_vpc_peering_connection.compute_to_data.id
}

resource "aws_route" "data_to_compute" {
  count = length(data.terraform_remote_state.data.outputs.private_route_table_ids)

  route_table_id            = data.terraform_remote_state.data.outputs.private_route_table_ids[count.index]
  destination_cidr_block    = var.compute_vpc_cidr
  vpc_peering_connection_id = aws_vpc_peering_connection.compute_to_data.id
}
