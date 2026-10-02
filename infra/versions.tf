# Simulacra Americana's AWS stack: the simulation API (ECS Fargate behind an
# ALB, state on EFS), the assets CDN (CloudFront over a private S3 bucket) and
# the private census-derived data bucket. Same account and region as the
# Partyhat auth server, but nothing here references or modifies its resources;
# the only shared object read is the account's GitHub OIDC provider.
#
# State lives in s3://simulacra-americana-tfstate (infra/bootstrap.sh creates it).
# Apply order and the DNS steps between applies: docs/DEPLOY.md, "Stand-up".

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "s3" {
    bucket       = "simulacra-americana-tfstate"
    key          = "prod/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = ["735776117779"]
  default_tags {
    tags = { project = "simulacra-americana", managed-by = "terraform" }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.region
  name       = "simulacra"
}
