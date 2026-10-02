# infra/vercel-dns.sh reads these (terraform output -json); deploy-api.yml's
# repo variables are set from them (docs/DEPLOY.md, "CI setup").

output "acm_validation_records" {
  description = "CNAMEs to add in Vercel DNS before the certificates can issue."
  value = {
    for o in concat(tolist(aws_acm_certificate.api.domain_validation_options), tolist(aws_acm_certificate.assets.domain_validation_options)) :
    o.domain_name => { name = o.resource_record_name, type = o.resource_record_type, value = o.resource_record_value }
  }
}

output "api_alb_dns_name" {
  description = "Target of the api. CNAME."
  value       = aws_lb.api.dns_name
}

output "assets_cloudfront_domain" {
  description = "Target of the assets. CNAME."
  value       = aws_cloudfront_distribution.assets.domain_name
}

output "assets_distribution_id" {
  value = aws_cloudfront_distribution.assets.id
}

output "deploy_role_arn" {
  description = "Repo variable AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.deploy.arn
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

# Everything deploy-api.yml needs to render infra/taskdef.json.tftpl
# (repo variable TASKDEF_VARS, as JSON). Image is filled in per deploy.
output "taskdef_vars" {
  value = { for k, v in local.taskdef_vars : k => v if k != "image" }
}

output "seed_task" {
  description = "For scripts/sync-data.sh: aws ecs run-task parameters."
  value = {
    cluster         = aws_ecs_cluster.main.name
    task_definition = aws_ecs_task_definition.seed.family
    subnets         = var.subnet_ids
    security_group  = aws_security_group.task.id
  }
}
