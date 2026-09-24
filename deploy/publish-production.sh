#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

command -v docker >/dev/null || { echo 'Docker is required'; exit 1; }
command -v openssl >/dev/null || { echo 'OpenSSL is required'; exit 1; }

if [ ! -f .env ]; then
  cp deploy/.env.production.example .env
  sed -i "s#CHANGE_ME_SESSION_SECRET#$(openssl rand -hex 32)#" .env
  sed -i "s#CHANGE_ME_WORKER_TOKEN#$(openssl rand -hex 32)#" .env
  echo '.env created. Set DOMAIN, POSTGRES_PASSWORD and PACKAGE_MIRROR_URL before continuing.'
  exit 2
fi

set -a; . ./.env; set +a
: "${DOMAIN:?DOMAIN is required in .env}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required in .env}"
: "${PACKAGE_MIRROR_URL:?PACKAGE_MIRROR_URL is required in .env}"

python3 - <<'PY'
from pathlib import Path
import os
p=Path('deploy/Caddyfile')
s=p.read_text()
s=s.replace('ide.example.com', os.environ['DOMAIN'])
p.write_text(s)
PY

docker compose --env-file .env -f deploy/docker-compose.cloud.yml config >/dev/null
docker compose --env-file .env -f deploy/docker-compose.cloud.yml up -d --build
docker compose --env-file .env -f deploy/docker-compose.cloud.yml ps
printf '\nDeployment started for https://%s\n' "$DOMAIN"
