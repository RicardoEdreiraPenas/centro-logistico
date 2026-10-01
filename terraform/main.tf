# AMI: Amazon Linux 2023 (eu-west-3, x86_64, most recent)
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# Key pair — generated in Terraform, private key saved locally
resource "tls_private_key" "logistics" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "logistics" {
  key_name   = "logistics-key"
  public_key = tls_private_key.logistics.public_key_openssh
}

resource "local_sensitive_file" "pem" {
  content         = tls_private_key.logistics.private_key_pem
  filename        = "${path.module}/logistics.pem"
  file_permission = "0400"
}

# IAM role — allows EC2 instances to access SQS without hardcoded keys
resource "aws_iam_role" "logistics_ec2" {
  name = "logistics-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "sqs_access" {
  name = "sqs-truck-events"
  role = aws_iam_role.logistics_ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueUrl",
        "sqs:GetQueueAttributes"
      ]
      Resource = "arn:aws:sqs:eu-north-1:*:truck-events"
    }]
  })
}

resource "aws_iam_instance_profile" "logistics_ec2" {
  name = "logistics-ec2-profile"
  role = aws_iam_role.logistics_ec2.name
}

# Security group — SSH + client API + Metabase
resource "aws_security_group" "logistics_ec2" {
  name        = "logistics-ec2-sg"
  description = "Logistics center EC2 instances"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Client API + floor plan"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Metabase"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "logistics-ec2-sg" }
}
