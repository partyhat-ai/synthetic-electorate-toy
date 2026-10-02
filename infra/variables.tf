variable "domain" {
  description = "The site's apex domain (DNS hosted at Vercel)."
  type        = string
  default     = "simulacraamericana.com"
}

variable "subnet_ids" {
  description = "Default-VPC public subnets for the ALB, the task and EFS (the auth server's two AZs, us-east-1a/b)."
  type        = list(string)
  default     = ["subnet-8c3db5ea", "subnet-35f36514"]
}

variable "image" {
  description = "The API image for the FIRST task-definition revision only. CI registers every later one from infra/taskdef.json.tftpl; the service ignores task-definition drift."
  type        = string
  default     = "public.ecr.aws/docker/library/busybox:latest"
}

variable "task_cpu" {
  type    = number
  default = 1024
}

variable "task_memory" {
  description = "MiB. The worker loads pandas/scipy plus a run's draws alongside Node."
  type        = number
  default     = 4096
}

variable "alert_email" {
  description = "Subscriber for the alarm topic. SNS emails a confirmation link that must be clicked."
  type        = string
}

variable "monthly_budget_usd" {
  description = "AWS Budgets alert threshold for this stack (AWS spend only; Anthropic spend is alerted in the Anthropic console)."
  type        = number
  default     = 150
}

variable "github_oidc_sub" {
  description = "The deploy role's trusted OIDC sub, with the org's numeric ids: repo:partyhat-ai@44511702/<repo>@<repoId>:*. Read the real claim from a test run; repo:owner/name:* silently never matches."
  type        = string
}

variable "cors_origins" {
  description = "Origins allowed to fetch robot assets (three.js fetches GLBs and textures cross-origin)."
  type        = list(string)
  # The site, plus local builds (pnpm serve :8790, vite dev :5173, vite preview :4173)
  # so the 3D robot loads when the page is run on a laptop.
  default = ["https://simulacraamericana.com", "http://localhost:8790", "http://localhost:5173", "http://localhost:4173"]
}
