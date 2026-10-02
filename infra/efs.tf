# The service's state: serve/bundles, sessions, runs, whatifs, configs and
# the census-derived cache, all under one access point owned by the image's
# `app` user (uid 1000). The image symlinks the code-relative folders here.

resource "aws_efs_file_system" "state" {
  creation_token   = "${local.name}-state"
  encrypted        = true
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }
  tags = { Name = "${local.name}-state" }
}

resource "aws_efs_mount_target" "state" {
  for_each        = toset(var.subnet_ids)
  file_system_id  = aws_efs_file_system.state.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "state" {
  file_system_id = aws_efs_file_system.state.id
  posix_user {
    uid = 1000
    gid = 1000
  }
  root_directory {
    path = "/simulacra"
    creation_info {
      owner_uid   = 1000
      owner_gid   = 1000
      permissions = "0755"
    }
  }
  tags = { Name = "${local.name}-state" }
}

# Only through the access point, only over TLS, only by the task role.
resource "aws_efs_file_system_policy" "state" {
  file_system_id = aws_efs_file_system.state.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "TaskRoleViaAccessPoint"
        Effect    = "Allow"
        Principal = { AWS = aws_iam_role.task.arn }
        Action    = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"]
        Resource  = aws_efs_file_system.state.arn
        Condition = {
          StringEquals = { "elasticfilesystem:AccessPointArn" = aws_efs_access_point.state.arn }
          Bool         = { "aws:SecureTransport" = "true" }
        }
      }
    ]
  })
}
