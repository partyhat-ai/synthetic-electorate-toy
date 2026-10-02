resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/simulacra"
  retention_in_days = 30
}

# A real subscriber this time (the auth server's topic had none). SNS emails a
# confirmation link; alarms go nowhere until it's clicked.
resource "aws_sns_topic" "alarms" {
  name = "${local.name}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

locals {
  alb_dims = { LoadBalancer = aws_lb.api.arn_suffix, TargetGroup = aws_lb_target_group.api.arn_suffix }
}

resource "aws_cloudwatch_metric_alarm" "no_healthy_target" {
  alarm_name          = "${local.name}-no-healthy-target"
  alarm_description   = "The API has had no healthy task for 3 minutes."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HealthyHostCount"
  dimensions          = local.alb_dims
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 3
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "target_5xx" {
  alarm_name          = "${local.name}-target-5xx"
  alarm_description   = "The API returned 5xx responses (more than 5 in 5 minutes)."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  dimensions          = { LoadBalancer = aws_lb.api.arn_suffix }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 5
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "elb_5xx" {
  alarm_name          = "${local.name}-elb-5xx"
  alarm_description   = "The load balancer itself returned 5xx (no target, or target timeouts)."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_ELB_5XX_Count"
  dimensions          = { LoadBalancer = aws_lb.api.arn_suffix }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

# The worker's log (sessions/intake.log) is echoed to stdout with a
# "[worker]" prefix by docker/entrypoint.sh.
resource "aws_cloudwatch_log_metric_filter" "worker_failure" {
  name           = "${local.name}-worker-failure"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "?\"[worker] STOP:\" ?\"[worker] Traceback\" ?refusing ?\"worker failed to start\""
  metric_transformation {
    name          = "WorkerFailures"
    namespace     = "Simulacra"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "worker_failure" {
  alarm_name          = "${local.name}-worker-failure"
  alarm_description   = "The what-if worker stopped, refused, or raised. Read /ecs/simulacra for [worker] lines."
  namespace           = "Simulacra"
  metric_name         = "WorkerFailures"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

# Budgets filter on the project tag, which must be an active cost-allocation tag.
resource "aws_ce_cost_allocation_tag" "project" {
  tag_key = "project"
  status  = "Active"
}

resource "aws_budgets_budget" "stack" {
  name         = "${local.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  cost_filter {
    name   = "TagKeyValue"
    values = ["user:project$simulacra-americana"]
  }
  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "FORECASTED"
    subscriber_sns_topic_arns = [aws_sns_topic.alarms.arn]
  }
  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.alarms.arn]
  }
}

# Budgets publishes to the topic only if the topic lets it.
resource "aws_sns_topic_policy" "alarms" {
  arn = aws_sns_topic.alarms.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AccountOwner"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${local.account_id}:root" }
        Action    = ["SNS:Publish", "SNS:Subscribe", "SNS:GetTopicAttributes", "SNS:SetTopicAttributes", "SNS:ListSubscriptionsByTopic"]
        Resource  = aws_sns_topic.alarms.arn
      },
      {
        Sid       = "CloudWatchAlarms"
        Effect    = "Allow"
        Principal = { Service = "cloudwatch.amazonaws.com" }
        Action    = "SNS:Publish"
        Resource  = aws_sns_topic.alarms.arn
      },
      {
        Sid       = "Budgets"
        Effect    = "Allow"
        Principal = { Service = "budgets.amazonaws.com" }
        Action    = "SNS:Publish"
        Resource  = aws_sns_topic.alarms.arn
      }
    ]
  })
}
