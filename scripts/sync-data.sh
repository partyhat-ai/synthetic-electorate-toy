#!/usr/bin/env bash
# Census-derived data and service state: laptop -> private data bucket -> EFS.
# Re-runnable. Nothing here ever writes to git, an image, Vercel or the assets bucket.
#
#   scripts/sync-data.sh upload-cache   laptop harness_cache (minus */raw/) -> s3://.../cache/
#   scripts/sync-data.sh upload-seed    repo bundles/whatifs/configs/runs + laptop runs/_cache -> s3://.../seed/
#   scripts/sync-data.sh seed           one-off ECS task: seed -> EFS (refuses if already seeded)
#   scripts/sync-data.sh cache          one-off ECS task: cache -> EFS/cache (replaces it)
#   scripts/sync-data.sh backup         tarball the laptop's harness state + cache to s3://.../backups/<date>/
#
# The run id hashes the cache's manifest: the bytes on EFS must match the
# laptop's for run ids to line up, so the cache is synced byte-for-byte.
#
# Note: on aws-cli 2.23.4 (this laptop) `aws s3 cp` of a multipart object
# DOWN from this versioned bucket fails with NoSuchKey; `aws s3api get-object`
# works. Uploads and small-file syncs are unaffected.
set -euo pipefail

B=s3://simulacra-americana-data
REPO=$(cd "$(dirname "$0")/.." && pwd)
CACHE=${SIMHARNESS_CACHE:-$HOME/research_notes/historical_election_sim_data/harness_cache}
# The live harness the laptop has been running (its runs/_cache is the answer cache).
LAPTOP_HARNESS=${LAPTOP_HARNESS:-$HOME/Documents/fromDesktop/quickmoveaway/vaultSYncWebWithLocalOPtion/vaultsync-chatwindows/src/lib/simulacra/harness}
test "$(aws sts get-caller-identity --query Account --output text)" = 735776117779

run_task() {
  local mode=$1 o
  o=$(cd "$REPO/infra" && terraform output -json seed_task)
  local cluster td subnets sg
  cluster=$(jq -r .cluster <<<"$o"); td=$(jq -r .task_definition <<<"$o")
  subnets=$(jq -r '.subnets | join(",")' <<<"$o"); sg=$(jq -r .security_group <<<"$o")
  local arn
  arn=$(aws ecs run-task --cluster "$cluster" --task-definition "$td" --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$subnets],securityGroups=[$sg],assignPublicIp=ENABLED}" \
    --overrides "{\"containerOverrides\":[{\"name\":\"seed\",\"environment\":[{\"name\":\"MODE\",\"value\":\"$mode\"}]}]}" \
    --query 'tasks[0].taskArn' --output text)
  echo "started $arn; waiting"
  aws ecs wait tasks-stopped --cluster "$cluster" --tasks "$arn"
  aws ecs describe-tasks --cluster "$cluster" --tasks "$arn" \
    --query 'tasks[0].containers[0].[exitCode,reason]' --output text
  echo "logs: aws logs tail /ecs/simulacra --log-stream-name-prefix seed --since 15m"
}

case "${1:-}" in
  upload-cache)
    aws s3 sync "$CACHE/" "$B/cache/" --exclude '*/raw/*' --exclude '.DS_Store' --only-show-errors
    aws s3 ls "$B/cache/" --recursive --summarize | tail -2 ;;
  upload-seed)
    for d in whatifs configs; do
      aws s3 sync "$REPO/$d/" "$B/seed/$d/" --exclude '.DS_Store' --only-show-errors
    done
    aws s3 sync "$REPO/serve/bundles/" "$B/seed/bundles/" --exclude '.DS_Store' --only-show-errors
    aws s3 sync "$REPO/runs/" "$B/seed/runs/" --exclude '.DS_Store' --only-show-errors
    # The answer cache and pickles aren't in git; they come from the laptop.
    aws s3 sync "$LAPTOP_HARNESS/runs/_cache/" "$B/seed/runs/_cache/" --exclude '.DS_Store' --only-show-errors
    aws s3 ls "$B/seed/" --recursive --summarize | tail -2 ;;
  seed)  run_task seed ;;
  cache) run_task cache ;;
  backup)
    d=$(date +%F); tmp=$(mktemp -d)
    (cd "$LAPTOP_HARNESS" && COPYFILE_DISABLE=1 tar czf "$tmp/harness-state-$d.tgz" serve/bundles sessions runs whatifs configs)
    (cd "$CACHE" && COPYFILE_DISABLE=1 tar czf "$tmp/harness-cache-derived-$d.tgz" --exclude='*/raw' .)
    (cd "$tmp" && shasum -a 256 ./*.tgz > SHA256SUMS)
    aws s3 cp "$tmp/" "$B/backups/$d/" --recursive --only-show-errors
    cat "$tmp/SHA256SUMS"; rm -rf "$tmp" ;;
  *)
    sed -n '2,12p' "$0"; exit 2 ;;
esac
