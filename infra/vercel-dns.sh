#!/usr/bin/env bash
# Every DNS record the AWS side needs, added in Vercel DNS (the zone lives
# there; scope camerons-projects-2a650f0d). Prints the commands by default;
# --apply runs them. Each run needs Cameron's yes: these change production DNS.
#
#   infra/vercel-dns.sh certs [--apply]      before the full apply: CAA + ACM validation
#   infra/vercel-dns.sh endpoints [--apply]  after it: api. -> ALB, assets. -> CloudFront
#
# The zone before any change:
#   CAA   @  0 issue "pki.goog" | "sectigo.com" | "letsencrypt.org"   (Vercel defaults)
#   ALIAS @  cname.vercel-dns-016.com.
#   ALIAS *  cname.vercel-dns-016.com.
# The explicit api/assets/_validation names below take precedence over the *
# wildcard. Without the amazon.com CAA record ACM never issues.
set -euo pipefail

DOMAIN=simulacraamericana.com
MODE=${1:-}
APPLY=${2:-}
cd "$(dirname "$0")"
out() { terraform output -json "$1"; }

run() {
  if [ "$APPLY" = "--apply" ]; then "$@"; else printf '%q ' "$@"; echo; fi
}

# A name relative to the zone ("_abc.api.simulacraamericana.com." -> "_abc.api").
rel() { local n=${1%.}; echo "${n%.$DOMAIN}"; }

case "$MODE" in
  certs)
    run vercel dns add "$DOMAIN" '@' CAA '0 issue "amazon.com"'
    out acm_validation_records | python3 -c '
import json, sys
for r in json.load(sys.stdin).values():
    print(r["name"], r["value"])' | while read -r name value; do
      run vercel dns add "$DOMAIN" "$(rel "$name")" CNAME "${value%.}"
    done
    ;;
  endpoints)
    run vercel dns add "$DOMAIN" api CNAME "$(out api_alb_dns_name | tr -d '"')"
    run vercel dns add "$DOMAIN" assets CNAME "$(out assets_cloudfront_domain | tr -d '"')"
    ;;
  *)
    echo "usage: $0 certs|endpoints [--apply]" >&2
    exit 2
    ;;
esac
if [ "$APPLY" = "--apply" ]; then vercel dns ls "$DOMAIN"; fi
