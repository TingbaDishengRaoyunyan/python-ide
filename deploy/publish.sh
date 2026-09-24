#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Docker is required'; exit 1; }
[ -f .env ] || { cp deploy/.env.production.example .env; sed -i "s#replace-with-output-of-openssl-rand-hex-32#$(openssl rand -hex 32)#" .env; echo "WORKER_TOKEN=$(openssl rand -hex 32)" >> .env; }
: "${DOMAIN:?Set DOMAIN in .env or export DOMAIN}"
sed -i "s#ide.example.com#${DOMAIN}#" deploy/Caddyfile
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
docker compose -f docker-compose.prod.yml --env-file .env ps
