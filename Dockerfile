# syntax=docker/dockerfile:1

# The simulation API: the Express router (Node 22) and the harness worker it
# spawns (Python 3.13) in one container. ARM64 (Fargate Graviton), built on a
# native ARM runner by .github/workflows/deploy-api.yml.
#
# The image holds code only. Everything the worker writes (serve/bundles,
# sessions, runs, whatifs, configs) and the census-derived cache live on EFS
# at /state; see "State" below. No secrets and no cache data are in any layer:
# ANTHROPIC_API_KEY arrives from Secrets Manager at runtime.

# ---------------------------------------------------------------------------
# Stage 1: the server bundle (dev dependencies, esbuild)
# ---------------------------------------------------------------------------
FROM node:22-bookworm-slim AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile --ignore-scripts
COPY serve ./serve
# express and zod stay external and come from the prod install below.
# esbuild is vite's dependency; pnpm hoists it into .pnpm/node_modules.
RUN node node_modules/.pnpm/node_modules/esbuild/bin/esbuild serve/server.ts \
      --bundle --platform=node --format=esm --target=node22 --packages=external \
      --outfile=dist/server.mjs

# ---------------------------------------------------------------------------
# Stage 2: production node_modules only (express, zod, ...)
# ---------------------------------------------------------------------------
FROM node:22-bookworm-slim AS prod-deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile --prod --ignore-scripts

# ---------------------------------------------------------------------------
# Stage 3: the harness venv
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS pydeps
COPY requirements.lock /tmp/requirements.lock
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv && /opt/venv/bin/pip install -r /tmp/requirements.lock

# ---------------------------------------------------------------------------
# Stage 4: runtime
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS runtime

# Node comes from the official image (same major as CI); no npm, no toolchain.
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=pydeps /opt/venv /opt/venv

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 1000 --create-home app

WORKDIR /app
COPY --from=prod-deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json pyproject.toml ./
COPY simharness ./simharness
COPY extracts ./extracts
COPY profiles ./profiles
COPY docker/entrypoint.sh /usr/local/bin/simulacra-entrypoint

# State. The harness derives every path from its own location (config.py
# ROOT = the folder above simharness/), and intake.py writes ROOT/serve/bundles
# whatever SIMULACRA_BUNDLES says. So the code-relative folders are symlinks
# onto the EFS mount, and both the router and the worker see the same files.
# EFS is seeded once by the seed task (scripts/sync-data.sh), never from here.
RUN mkdir -p serve \
 && ln -s /state/bundles  serve/bundles \
 && ln -s /state/sessions sessions \
 && ln -s /state/runs     runs \
 && ln -s /state/whatifs  whatifs \
 && ln -s /state/configs  configs

ENV NODE_ENV=production \
    PORT=8080 \
    SIMULACRA_LOG=1 \
    SIMULACRA_AUTORUN=configs/live-1920.json \
    SIMULACRA_PYTHON=/opt/venv/bin/python \
    SIMULACRA_BUNDLES=/app/serve/bundles \
    SIMHARNESS_CACHE=/state/cache \
    PYTHONUNBUFFERED=1
EXPOSE 8080
USER app

# Exec form. In ECS, initProcessEnabled puts tini at PID 1; the entrypoint
# execs node, so node receives SIGTERM directly (serve/server.ts handles it).
ENTRYPOINT ["/usr/local/bin/simulacra-entrypoint"]
CMD ["node", "dist/server.mjs"]
