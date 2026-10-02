# The shell only. The value is put by hand, never through Terraform, so it
# never lands in state or git. It is JSON with two fields:
#   ANTHROPIC_API_KEY      the model key
#   SIMULACRA_ACCESS_KEYS  a JSON object (as a string) of name → access key; a
#                          request needs one to queue new text (serve/guard.ts)
# docs/DEPLOY.md "Access keys" has the command.
# The IPUMS/NHGIS key is only for rebuilding the cache on a laptop; never here.

resource "aws_secretsmanager_secret" "prod" {
  name                    = "simulacra/prod"
  description             = "Simulacra API runtime secrets (ANTHROPIC_API_KEY, SIMULACRA_ACCESS_KEYS)"
  recovery_window_in_days = 7
}
