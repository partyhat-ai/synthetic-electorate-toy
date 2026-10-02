# Daily EFS backups, 35 days. Production state diverges from git the moment
# the worker models anything, and 46 of the 60 bundles can't be regenerated.

resource "aws_backup_vault" "state" {
  name = "${local.name}-state"
}

resource "aws_backup_plan" "state" {
  name = "${local.name}-state-daily"
  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.state.name
    schedule          = "cron(0 7 * * ? *)"
    lifecycle { delete_after = 35 }
  }
}

data "aws_iam_policy_document" "backup_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backup" {
  name               = "${local.name}-backup"
  assume_role_policy = data.aws_iam_policy_document.backup_assume.json
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "restore" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

resource "aws_backup_selection" "state" {
  name         = "${local.name}-efs"
  plan_id      = aws_backup_plan.state.id
  iam_role_arn = aws_iam_role.backup.arn
  resources    = [aws_efs_file_system.state.arn]
}
