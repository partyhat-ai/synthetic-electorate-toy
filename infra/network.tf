# The auth server's network pattern: default-VPC public subnets, tasks with a
# public IP, no NAT gateway (~$32/mo saved). Only the ALB is reachable from
# the internet; the task accepts its port from the ALB alone, EFS accepts NFS
# from the tasks alone.

data "aws_subnet" "selected" {
  for_each = toset(var.subnet_ids)
  id       = each.value
}

locals {
  vpc_id = one(distinct([for s in data.aws_subnet.selected : s.vpc_id]))
}

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Simulacra API load balancer: HTTP/HTTPS from anywhere"
  vpc_id      = local.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "alb_to_task" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_security_group" "task" {
  name        = "${local.name}-task"
  description = "Simulacra API task: app port from the ALB only"
  vpc_id      = local.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "task_from_alb" {
  security_group_id            = aws_security_group.task.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

# Out to Anthropic, ECR, Secrets Manager, S3, logs (no NAT: via the public IP).
resource "aws_vpc_security_group_egress_rule" "task_all" {
  security_group_id = aws_security_group.task.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "efs" {
  name        = "${local.name}-efs"
  description = "Simulacra state: NFS from the API and seed tasks only"
  vpc_id      = local.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "efs_from_task" {
  security_group_id            = aws_security_group.efs.id
  referenced_security_group_id = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
}
