#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

command -v docker >/dev/null || { echo 'Docker is required'; exit 1; }
[ -f .env ] || cp deploy/.env.production.example .env

set -a
. ./.env
set +a

: "${DOMAIN:?DOMAIN is required in .env}"
: "${SESSION_SECRET:?SESSION_SECRET is required in .env}"
: "${WORKER_TOKEN:?WORKER_TOKEN is required in .env}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required in .env}"

python3 - <<'PY'
import os
from pathlib import Path
path = Path('deploy/Caddyfile')
text = path.read_text()
text = text.replace('ide.example.com', os.environ['DOMAIN'])
path.write_text(text)
PY

docker compose --env-file .env -f deploy/docker-compose.cloud.yml config >/dev/null

docker compose --env-file .env -f deploy/docker-compose.cloud.yml up -d --build
docker compose --env-file .env -f deploy/docker-compose.cloud.yml ps

echo "Deployment started for https://${DOMAIN}"
