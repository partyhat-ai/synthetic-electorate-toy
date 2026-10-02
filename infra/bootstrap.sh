#!/usr/bin/env bash
# One-time: the Terraform state bucket. Re-runnable (every step is idempotent).
# Run before the first `terraform init`.
set -euo pipefail

B=simulacra-americana-tfstate
test "$(aws sts get-caller-identity --query Account --output text)" = 735776117779

if ! aws s3api head-bucket --bucket "$B" 2>/dev/null; then
  aws s3api create-bucket --bucket "$B" --region us-east-1 --object-ownership BucketOwnerEnforced >/dev/null
fi
aws s3api put-public-access-block --bucket "$B" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-encryption --bucket "$B" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"},"BucketKeyEnabled":true}]}'
aws s3api put-bucket-versioning --bucket "$B" --versioning-configuration Status=Enabled
aws s3api put-bucket-tagging --bucket "$B" --tagging 'TagSet=[{Key=project,Value=simulacra-americana}]'
echo "state bucket $B ready"
