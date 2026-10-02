# One cluster, one service, ONE task, on purpose: run state is an in-process
# Map, the worker lock is a PID file (PIDs aren't unique across containers),
# and two tasks would run two workers against the same EFS queue. So
# desiredCount 1 and the old task stops before the new one starts
# (minimumHealthyPercent 0 / maximumPercent 100): a few seconds of 503 per
# deploy. The circuit breaker rolls back a revision that never gets healthy.
#
# The task definition is rendered from infra/taskdef.json.tftpl, here for the
# first revision and by deploy-api.yml for every later one, so env and secrets
# can't silently drop on a deploy. The service ignores task-definition drift.

resource "aws_ecr_repository" "api" {
  name = "simulacra-api"
  # SHA tags are immutable; the one moving tag is the registry layer cache
  # deploy-api.yml writes on every build.
  image_tag_mutability = "IMMUTABLE_WITH_EXCLUSION"
  image_tag_mutability_exclusion_filter {
    filter      = "buildcache"
    filter_type = "WILDCARD"
  }
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 30 images (rollback depth)"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 30 }
      action       = { type = "expire" }
    }]
  })
}

resource "aws_ecs_cluster" "main" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

locals {
  taskdef_vars = {
    image              = var.image
    cpu                = var.task_cpu
    memory             = var.task_memory
    execution_role_arn = aws_iam_role.execution.arn
    task_role_arn      = aws_iam_role.task.arn
    efs_id             = aws_efs_file_system.state.id
    access_point_id    = aws_efs_access_point.state.id
    secret_arn         = aws_secretsmanager_secret.prod.arn
    log_group          = aws_cloudwatch_log_group.api.name
    region             = local.region
  }
  taskdef = jsondecode(templatefile("${path.module}/taskdef.json.tftpl", local.taskdef_vars))
}

resource "aws_ecs_task_definition" "api" {
  family                   = local.taskdef.family
  network_mode             = local.taskdef.networkMode
  requires_compatibilities = local.taskdef.requiresCompatibilities
  cpu                      = local.taskdef.cpu
  memory                   = local.taskdef.memory
  execution_role_arn       = local.taskdef.executionRoleArn
  task_role_arn            = local.taskdef.taskRoleArn
  container_definitions    = jsonencode(local.taskdef.containerDefinitions)
  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }
  volume {
    name = "state"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.state.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.state.id
        iam             = "ENABLED"
      }
    }
  }
  # Only the first revision comes from here (var.image at stand-up); CI
  # registers every later one from the same template.
  lifecycle { ignore_changes = [container_definitions] }
}

resource "aws_ecs_service" "api" {
  name                               = "simulacra-api"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.api.arn
  desired_count                      = 1
  launch_type                        = "FARGATE"
  platform_version                   = "LATEST"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  health_check_grace_period_seconds  = 60
  enable_execute_command             = false

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8080
  }

  lifecycle { ignore_changes = [task_definition] }
  depends_on = [aws_lb_listener.https, aws_efs_mount_target.state]
}

# A one-off task (scripts/sync-data.sh) that copies from the private data
# bucket onto EFS: `seed` once, `cache` whenever the census data changes.
resource "aws_ecs_task_definition" "seed" {
  family                   = "simulacra-seed"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }
  volume {
    name = "state"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.state.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.state.id
        iam             = "ENABLED"
      }
    }
  }
  container_definitions = jsonencode([{
    name       = "seed"
    image      = "public.ecr.aws/aws-cli/aws-cli:latest"
    essential  = true
    entryPoint = ["sh", "-c"]
    # MODE=seed copies only into an unseeded volume (marker file), so it can
    # never overwrite what production has written. MODE=cache replaces the
    # census-derived cache wholesale (read-only data).
    command = [<<-EOT
      set -eu
      case "$MODE" in
        seed)
          if [ -e /state/.seeded ]; then echo "already seeded; refusing"; exit 0; fi
          aws s3 sync "s3://${aws_s3_bucket.data.bucket}/seed/" /state/ --only-show-errors
          aws s3 sync "s3://${aws_s3_bucket.data.bucket}/cache/" /state/cache/ --only-show-errors
          date -u +%FT%TZ > /state/.seeded ;;
        cache)
          aws s3 sync "s3://${aws_s3_bucket.data.bucket}/cache/" /state/cache/ --delete --only-show-errors ;;
        *) echo "MODE must be seed or cache"; exit 2 ;;
      esac
      find /state -maxdepth 1 | sort
    EOT
    ]
    environment = [{ name = "MODE", value = "seed" }]
    mountPoints = [{ sourceVolume = "state", containerPath = "/state" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "seed"
      }
    }
  }])
}
