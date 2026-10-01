variable "region" {
  description = "AWS region for EC2 and RDS"
  type        = string
  default     = "eu-west-3"
}

variable "vpc_id" {
  description = "VPC ID where the security group will be created"
  type        = string
}

variable "subnet_id" {
  description = "Public subnet ID for EC2 instances"
  type        = string
}

variable "rds_host" {
  description = "Endpoint de la base de datos RDS PostgreSQL"
  type        = string
}

variable "rds_port" {
  description = "Puerto de RDS"
  type        = number
  default     = 5432
}

variable "rds_db" {
  description = "Nombre de la base de datos"
  type        = string
  default     = "postgres"
}

variable "rds_user" {
  description = "Usuario de la base de datos"
  type        = string
  default     = "postgres"
}

variable "rds_password" {
  description = "Contraseña de la base de datos (nunca en el repositorio)"
  type        = string
  sensitive   = true
}

variable "sqs_region" {
  description = "Región de las colas SQS"
  type        = string
  default     = "eu-north-1"
}
