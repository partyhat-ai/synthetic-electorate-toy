# Deploying Simulacra Americana

https://simulacraamericana.com. The page is a static SvelteKit build on
Vercel. The simulation API runs on AWS ECS Fargate at
api.simulacraamericana.com, which the page reaches through a same-origin
Vercel rewrite of `/api/simulacra/*`. The robot assets and portraits come
from CloudFront at assets.simulacraamericana.com. The census-derived data
stays in a private S3 bucket and on EFS. AWS account 735776117779, us-east-1.

```
simulacraamericana.com, www (Vercel DNS)
  └─ Vercel project: static build on Vercel's CDN
       └─ rewrite /api/simulacra/:path* → https://api.simulacraamericana.com/api/simulacra/:path*
api.     CNAME → ALB (ACM) → ECS service simulacra-api (1 task, ARM64; Node + Python worker)
                              EFS /state: bundles, sessions, runs, whatifs, configs, cache
                              Secrets Manager simulacra/prod: ANTHROPIC_API_KEY
assets.  CNAME → CloudFront (ACM, OAC) → private S3 simulacra-americana-assets
private S3 simulacra-americana-data: cache/, seed/, backups/
```

Everything on the AWS side is Terraform in `infra/`, with state in
`s3://simulacra-americana-tfstate`. DNS is at Vercel: `infra/vercel-dns.sh`
lists every record. Nothing here touches the Partyhat stacks. The only shared
object is the account's GitHub OIDC provider, which this stack reads but
doesn't manage.

## Why one task

Several things assume a single process:
- Run state is an in-process `Map`.
- The worker lock (`sessions/intake.lock`) is a PID file, and PIDs aren't
  unique across containers.
- Each process runs one worker.

Two tasks would run two workers on the same EFS queue. So the service runs
`desiredCount 1` with `minimumHealthyPercent 0` and `maximumPercent 100`:
the old task stops before the new one starts. That gives a few seconds of
503s per deploy. The deployment circuit breaker rolls back a revision that
never becomes healthy. Don't scale this service out until the lock and run
state move off the process (to DynamoDB conditional writes, or `flock` on
EFS).

## State on EFS

The harness derives every path from its own location. `intake.py` also writes
`ROOT/serve/bundles` whatever `SIMULACRA_BUNDLES` says. So the image has no
state of its own. Instead, `/app/{runs,sessions,whatifs,configs}` and
`/app/serve/bundles` are symlinks onto the EFS mount at `/state`, and the
census cache is at `/state/cache` (`SIMHARNESS_CACHE`).

Production diverges from git as soon as the worker models anything: it
republishes bundles and edits `configs/live-<year>.json`. EFS is the record
from then on, backed up daily by AWS Backup (35 days). A code deploy never
overwrites state. To bring a git change to configs or whatifs into
production, copy it onto EFS on purpose.

## Stand-up (once)

Each step marked ⛔ needs Cameron's yes.

1. `infra/bootstrap.sh` creates the state bucket.
2. `cd infra && terraform init && terraform plan`.
3. ⛔ Certificates first: `terraform apply -target=aws_acm_certificate.api -target=aws_acm_certificate.assets -target=aws_ecr_repository.api`.
4. ⛔ DNS for the certificates: `infra/vercel-dns.sh certs`, then
   `--apply`. This adds the `amazon.com` CAA record (without it ACM never
   issues; the zone allows only pki.goog, sectigo and letsencrypt) and the two
   validation CNAMEs.
5. The first image: build and push `linux/arm64` to
   `<ecr>/simulacra-api:<sha>`, either locally (`docker buildx build
   --platform linux/arm64 --push`) or from the workflow's build step.
6. Put the secret value, which never goes through Terraform:
   `aws secretsmanager put-secret-value --secret-id simulacra/prod --secret-string '{"ANTHROPIC_API_KEY":"…"}'`.
   Terraform creates the empty secret in step 7. If you want the value in
   place before the task first starts, run
   `terraform apply -target=aws_secretsmanager_secret.prod` first.
7. ⛔ `terraform apply -var image=<ecr>/simulacra-api:<sha>`. This waits for
   the certificates to issue, then creates everything else, including the
   bill-monthly items: ALB, EFS, CloudFront.
8. Seed state:
   - `scripts/sync-data.sh upload-cache` (270 objects, 15 MB).
   - `scripts/sync-data.sh upload-seed`.
   - `scripts/sync-data.sh seed`. It refuses if the volume is already seeded.

   The service's task exits with "not seeded" until this has run. ECS keeps
   retrying, so seed right after step 7.
9. Assets: `python3 scripts/mirror-portraits.py --out ../simulacra-assets`,
   then `scripts/publish-assets.sh`.
10. ⛔ DNS for the endpoints: `infra/vercel-dns.sh endpoints`, then `--apply`.
11. Confirm the SNS subscription email to cam@partyhat.ai. Until it's
    confirmed, alarms reach nobody.
12. Free reproducibility check on the server: a one-off task running
    `python -m simharness.run dryrun --year 1920` should plan without errors.
    New run ids mean the cache bytes differ from the laptop's.

## CI setup

1. Create `partyhat-ai/synthetic-voters-toy` and push.
2. The deploy role trusts `var.github_oidc_sub`. For this org the claim
   carries numeric ids (`repo:partyhat-ai@44511702/<repo>@<repoId>:*`). The
   documented `repo:owner/name:*` silently never matches. Read the real claim
   from a test run, put it in `infra/terraform.tfvars`, and apply.
3. Set the repo variables from Terraform's outputs:
   ```
   gh variable set AWS_DEPLOY_ROLE_ARN -b "$(terraform -chdir=infra output -raw deploy_role_arn)"
   gh variable set TASKDEF_VARS -b "$(terraform -chdir=infra output -json taskdef_vars)"
   ```
4. A `workflow_dispatch` workflow can only be dispatched once its file is on
   the default branch.

## Deploying

**API** (manual only; a merge never ships):
```
gh workflow run "Deploy API" -R partyhat-ai/synthetic-voters-toy -f confirm=DEPLOY
```
The workflow:
- renders the task definition from `infra/taskdef.json.tftpl` and fails if
  any variable, required env var or secret is missing;
- builds on an ARM runner and tags the image with the full commit SHA;
- registers the revision, updates the service and waits until it's stable;
- fails if the circuit breaker rolled back;
- checks through the load balancer: `/healthz` returns 200, and
  `/api/simulacra/elections/1920` is `simulated: true` with slices.

To change an env var or secret, edit the template; that is the only place
it's defined.

**Web:** Vercel builds a preview from every push. Promoting to production is
manual (`vercel promote <url>`) and needs Cameron's yes. After a promotion,
check that the site loads, a year opens through the rewrite, and the robot
loads from `assets.`.

## Rolling back

- **API:** run `aws ecs update-service --cluster simulacra --service simulacra-api --task-definition simulacra-api:<previous>`.
  Every revision was rendered from the full template, so an older revision
  still carries its env and secrets. This is unlike the auth server's
  derive-from-running deploys. An image's revision can be redeployed as long
  as ECR keeps the image (the last 30).
- **Web:** `vercel rollback`, or "Instant Rollback" to a previous production
  deployment in the dashboard.
- **State (EFS):**
  1. In AWS Backup, open vault `simulacra-state` and restore a recovery point
     to a new directory on the same filesystem.
  2. Stop the service (`desired-count 0`) and swap the directories.
  3. Start the service again.

  An EFS restore puts the files in `aws-backup-restore_<ts>/` at the
  filesystem root, outside the access point. Move them with a one-off task
  that mounts the root.
- **Bundles only:** the repo's committed `serve/bundles` and the tarballs in
  `s3://simulacra-americana-data/backups/<date>/` are the fallbacks. Copy the
  year's `<year>.json` onto `/state/bundles`. The router reloads it by mtime
  without a restart.

## Assets

Edit or add assets in the assets folder outside the repo, then run
`scripts/publish-assets.sh`, which uploads them and invalidates `/*`.

The robot files are copied, never moved, from the shared Partyhat bucket.
Only what the page loads is copied: `models/atlas-09-americana.glb` and
`models/atlas-09-americana-rerun/`.

The page versions assets with `?v=`, and CloudFront's cache key includes the
query string, so a new `?v=` takes effect immediately.

## Portraits and credits

`scripts/mirror-portraits.py` resolves each portrait through the Commons API
and writes `portraits/credits.json` with the author, licence and licence URL
taken from the API. 76 of the 77 are public domain. One
needs attribution: `roosevelt2`, CC BY 2.0, Leon Perskie. The About sources
must show that credit.

## Rotating the Anthropic key

1. Create a new key in the Anthropic console.
2. `aws secretsmanager put-secret-value --secret-id simulacra/prod --secret-string '{"ANTHROPIC_API_KEY":"<new>"}'`.
3. Force a new deployment so the task picks up the key:
   `aws ecs update-service --cluster simulacra --service simulacra-api --force-new-deployment`.
   This brings a few seconds of 503s, and it kills a running worker, whose
   what-if is retried.
4. Revoke the old key once the new task is healthy.
5. Move the console usage alert to the new key.

## Spend

What-ifs aren't capped, by decision; this is visibility, not a limit. The
worker prices every stage before sending it and records it in
`/state/sessions/spend.jsonl`. To read it, run a one-off task, or download
the latest AWS Backup recovery point. Typed text goes to
`sessions/requests.jsonl`, which is accepted as-is.

AWS can't see Anthropic spend. Set a usage alert on the production key in the
Anthropic console.

## Census data

The NHGIS/IPUMS extracts and the derived `population/*_nhgis.csv` files are
not for redistribution. They live only in `s3://simulacra-americana-data/cache/`
(the derived part, everything except `*/raw/`) and on EFS. They are never in
git, an image, Vercel or the assets bucket.

To re-sync after rebuilding the cache on a laptop, run
`scripts/sync-data.sh upload-cache`, then `scripts/sync-data.sh cache`. Run
ids hash the cache manifest, so a changed cache means new run ids.

## Alarms

All alarms go to SNS `simulacra-alarms`, which emails cam@partyhat.ai:
- no healthy target for 3 minutes;
- more than 5 target 5xx in 5 minutes;
- more than 10 ELB 5xx in 5 minutes;
- any worker STOP, refusal or traceback (the entrypoint echoes worker lines
  to the log with a `[worker]` prefix);
- the AWS Budget forecast passing 80%, and actual spend passing 100% of $150
  a month. The budget filters on the `project` cost-allocation tag. AWS can
  take up to 24 hours to see a new tag, so activating it may fail on the
  first apply; re-apply the next day.

## Cost estimate (us-east-1, October 2026 list prices)

| Item | Basis | ~/month |
|---|---|---|
| ALB | $16.43 base plus about 1 LCU | $22 |
| Fargate | 1 vCPU, 4 GB, ARM, 24/7 | $34 |
| Public IPv4 | Task plus 2 ALB addresses at $3.65 each | $11 |
| EFS (elastic) | About 1–2 GB, growing 5–7 MB per new what-if, plus I/O | $1–3 |
| AWS Backup | EFS warm storage | <$1 |
| CloudFront | About 19 MB per first-time visitor; inside the 1 TB/month free tier up to about 50k visitors | $0 |
| S3, ECR, logs, alarms, Secrets Manager | | $3–5 |
| **AWS total** | | **≈ $75–80** |
| Vercel | Hobby is $0, but its terms exclude commercial use; Pro is $20 per member | $0–20 |
| Anthropic | $0.74–$1.91 per new typed what-if. Repeats and precomputed combinations are free | 10 a day ≈ $220–575; 100 a day ≈ $2.2k–5.7k |

The Anthropic line dominates. It has no cap, by decision (§1.2 of the deploy
prompt).
