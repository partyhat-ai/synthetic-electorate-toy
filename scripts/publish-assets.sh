#!/usr/bin/env bash
# Publish the robot assets and mirrored portraits to s3://simulacra-americana-assets
# (served by CloudFront at assets.simulacraamericana.com) and invalidate.
# Re-runnable. The assets themselves are never in git.
#
#   scripts/publish-assets.sh [assets-dir]     default ../simulacra-assets
#
# Robot: COPIED (never moved) from the shared Partyhat bucket, only what the
# page loads (src/lib/robot: models/atlas-09-americana.glb and its rerun paint
# set). Portraits: from scripts/mirror-portraits.py's output.
set -euo pipefail

SRC=s3://partyhat-vaultsync-bucket/harness-assets
DST=s3://simulacra-americana-assets
ASSETS=${1:-$(cd "$(dirname "$0")/.." && pwd)/../simulacra-assets}
LONG='public, max-age=31536000, immutable'
test "$(aws sts get-caller-identity --query Account --output text)" = 735776117779

# Robot model and paint set (object-to-object copy, same account).
aws s3 cp "$SRC/models/atlas-09-americana.glb" "$DST/models/atlas-09-americana.glb" \
  --metadata-directive REPLACE --content-type model/gltf-binary --cache-control "$LONG" --only-show-errors
aws s3 cp "$SRC/models/atlas-09-americana-rerun/" "$DST/models/atlas-09-americana-rerun/" --recursive \
  --metadata-directive REPLACE --cache-control "$LONG" --only-show-errors
# --metadata-directive REPLACE drops the source content types; restore them.
for k in $(aws s3api list-objects-v2 --bucket simulacra-americana-assets --prefix models/atlas-09-americana-rerun/ \
             --query 'Contents[].Key' --output text); do
  case "$k" in
    *.json) ct=application/json ;; *.png) ct=image/png ;; *.jpg|*.jpeg) ct=image/jpeg ;;
    *.webp) ct=image/webp ;; *.ktx2) ct=image/ktx2 ;; *) continue ;;
  esac
  aws s3 cp "$DST/$k" "$DST/$k" --metadata-directive REPLACE --content-type "$ct" \
    --cache-control "$LONG" --only-show-errors
done

# Portraits and their credits (credits change when a portrait does: short cache).
if [ -d "$ASSETS/portraits" ]; then
  aws s3 sync "$ASSETS/portraits/" "$DST/portraits/" --exclude '*' --include '*.jpg' \
    --content-type image/jpeg --cache-control "$LONG" --only-show-errors
  aws s3 cp "$ASSETS/portraits/credits.json" "$DST/portraits/credits.json" \
    --content-type application/json --cache-control 'public, max-age=3600' --only-show-errors
else
  echo "no $ASSETS/portraits; run scripts/mirror-portraits.py --out $ASSETS first" >&2
fi

aws s3 ls "$DST/" --recursive --summarize | tail -2

# Invalidate (the distribution exists only after the stand-up apply).
DIST=$(cd "$(dirname "$0")/../infra" && terraform output -raw assets_distribution_id 2>/dev/null || true)
if [ -n "$DIST" ]; then
  aws cloudfront create-invalidation --distribution-id "$DIST" --paths '/*' \
    --query 'Invalidation.[Id,Status]' --output text
fi
