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

variable "allowed_ssh_cidr" {
  description = "Rango CIDR desde el que se permite SSH (puerto 22). Normalmente tu IP pública con /32, por ejemplo \"203.0.113.10/32\". Sin valor por defecto para no abrir SSH a todo Internet por descuido."
  type        = string

  validation {
    condition     = can(cidrhost(var.allowed_ssh_cidr, 0)) && var.allowed_ssh_cidr != "0.0.0.0/0"
    error_message = "allowed_ssh_cidr debe ser un CIDR válido y distinto de 0.0.0.0/0 (por ejemplo \"203.0.113.10/32\")."
  }
}

variable "app_ingress_cidrs" {
  description = "Rangos CIDR que pueden acceder a la API de pedidos (8080) y a Metabase (3000). Por defecto la lista está vacía y esos puertos quedan cerrados; añade tu IP (\"203.0.113.10/32\") o, solo si quieres una demo pública, \"0.0.0.0/0\"."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for c in var.app_ingress_cidrs : can(cidrhost(c, 0))])
    error_message = "Todos los valores de app_ingress_cidrs deben ser rangos CIDR válidos."
  }
}
