locals {
  # Configuración que se inyecta en el arranque de cada instancia.
  # Los valores sensibles llegan desde terraform.tfvars (no versionado).
  app_env = {
    rds_host     = var.rds_host
    rds_port     = var.rds_port
    rds_db       = var.rds_db
    rds_user     = var.rds_user
    rds_password = var.rds_password
    sqs_region   = var.sqs_region
  }

  common = {
    ami                         = data.aws_ami.al2023.id
    subnet_id                   = var.subnet_id
    key_name                    = aws_key_pair.logistics.key_name
    vpc_security_group_ids      = [aws_security_group.logistics_ec2.id]
    iam_instance_profile        = aws_iam_instance_profile.logistics_ec2.name
    associate_public_ip_address = true
  }
}

resource "aws_instance" "truck_app" {
  ami                         = local.common.ami
  instance_type               = "t3.micro"
  subnet_id                   = local.common.subnet_id
  key_name                    = local.common.key_name
  vpc_security_group_ids      = local.common.vpc_security_group_ids
  iam_instance_profile        = local.common.iam_instance_profile
  associate_public_ip_address = local.common.associate_public_ip_address
  user_data                   = templatefile("${path.module}/user_data/truck_app.sh", local.app_env)

  tags = { Name = "truck-app" }
}

resource "aws_instance" "dock_app" {
  ami                         = local.common.ami
  instance_type               = "t3.micro"
  subnet_id                   = local.common.subnet_id
  key_name                    = local.common.key_name
  vpc_security_group_ids      = local.common.vpc_security_group_ids
  iam_instance_profile        = local.common.iam_instance_profile
  associate_public_ip_address = local.common.associate_public_ip_address
  user_data                   = templatefile("${path.module}/user_data/dock_app.sh", local.app_env)

  tags = { Name = "dock-app" }
}

resource "aws_instance" "client_app" {
  ami                         = local.common.ami
  instance_type               = "t3.micro"
  subnet_id                   = local.common.subnet_id
  key_name                    = local.common.key_name
  vpc_security_group_ids      = local.common.vpc_security_group_ids
  iam_instance_profile        = local.common.iam_instance_profile
  associate_public_ip_address = local.common.associate_public_ip_address
  user_data                   = templatefile("${path.module}/user_data/client_app.sh", local.app_env)

  tags = { Name = "client-app" }
}

resource "aws_instance" "el_logistics" {
  ami                         = local.common.ami
  instance_type               = "t3.micro"
  subnet_id                   = local.common.subnet_id
  key_name                    = local.common.key_name
  vpc_security_group_ids      = local.common.vpc_security_group_ids
  iam_instance_profile        = local.common.iam_instance_profile
  associate_public_ip_address = local.common.associate_public_ip_address
  user_data                   = templatefile("${path.module}/user_data/el_logistics.sh", local.app_env)

  tags = { Name = "el-logistics" }
}

resource "aws_instance" "metabase" {
  ami                         = local.common.ami
  instance_type               = "t3.small"
  subnet_id                   = local.common.subnet_id
  key_name                    = local.common.key_name
  vpc_security_group_ids      = local.common.vpc_security_group_ids
  iam_instance_profile        = local.common.iam_instance_profile
  associate_public_ip_address = local.common.associate_public_ip_address
  user_data                   = file("${path.module}/user_data/metabase.sh")

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = { Name = "metabase" }
}
