resource "aws_db_subnet_group" "postgres" {
  name       = "${var.project_name}-${var.environment}-data-db-subnet-group"
  subnet_ids = module.data_vpc.private_subnets
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-data-rds-sg"
  description = "Allows PostgreSQL from the compute VPC and data VPC Lambda"
  vpc_id      = module.data_vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.compute_vpc_cidr, var.data_vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "postgres" {
  identifier                  = "${var.project_name}-${var.environment}-db"
  engine                      = "postgres"
  engine_version              = "16"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  db_name                     = var.project_name
  username                    = var.db_username
  manage_master_user_password = true

  db_subnet_group_name      = aws_db_subnet_group.postgres.name
  vpc_security_group_ids    = [aws_security_group.rds.id]
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.project_name}-${var.environment}-data-final"

  lifecycle {
    prevent_destroy = true
  }
}
