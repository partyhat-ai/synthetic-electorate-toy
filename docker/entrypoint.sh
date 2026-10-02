#!/bin/sh
# The API container's entrypoint: check the state mount, surface the worker's
# log, then exec the server (so it, not this shell, gets SIGTERM).
set -eu

if [ ! -d /state/bundles ] || [ ! -d /state/configs ]; then
  echo "simulacra: /state is not seeded (no bundles/ or configs/). Run scripts/sync-data.sh seed." >&2
  exit 1
fi
mkdir -p /state/sessions /state/runs /state/whatifs

# The worker writes only to sessions/intake.log. Echo it to stdout so it
# reaches CloudWatch, where the worker-failure alarm reads it.
touch /state/sessions/intake.log
tail -n 0 -F /state/sessions/intake.log 2>/dev/null | sed -u 's/^/[worker] /' &

exec "$@"
