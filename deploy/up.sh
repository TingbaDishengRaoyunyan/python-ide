#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Docker is required'; exit 1; }
[ -f .env ] || { cp deploy/.env.production.example .env; sed -i "s#replace-with-output-of-openssl-rand-hex-32#$(openssl rand -hex 32)#" .env; echo 'Created .env; edit deploy/Caddyfile and register admin before public launch.'; }
if [ "${1:-}" = "gpu" ]; then docker compose -f docker-compose.gpu.yml --profile gpu up -d --build; else docker compose -f docker-compose.prod.yml --env-file .env up -d --build; fi
docker compose -f docker-compose.prod.yml --env-file .env ps
