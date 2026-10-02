# The shell only. The value (JSON {"ANTHROPIC_API_KEY": "..."}) is put by hand,
# never through Terraform, so it never lands in state or git:
#   aws secretsmanager put-secret-value --secret-id simulacra/prod \
#     --secret-string file://<(printf '{"ANTHROPIC_API_KEY":"%s"}' "$KEY")
# The IPUMS/NHGIS key is only for rebuilding the cache on a laptop; never here.

resource "aws_secretsmanager_secret" "prod" {
  name                    = "simulacra/prod"
  description             = "Simulacra API runtime secrets (ANTHROPIC_API_KEY)"
  recovery_window_in_days = 7
}
