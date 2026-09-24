# Complete deployment

## 1. Server preparation

Use Ubuntu 22.04/24.04 with Docker Engine and the Compose plugin. Open TCP ports 80 and 443 and point your domain's DNS record to the server.

## 2. Configure secrets and domain

```bash
cp deploy/.env.production.example .env
sed -i "s#replace-with-output-of-openssl-rand-hex-32#$(openssl rand -hex 32)#" .env
# Edit deploy/Caddyfile and replace ide.example.com
```

Keep `.env` private. Do not commit it.

## 3. Start

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
docker compose -f docker-compose.prod.yml ps
```

Caddy will request and renew the certificate automatically after DNS and ports are correct.

## 4. Create the administrator

`ADMIN_USERNAME_AUTO_PROMOTE=false` is intentional: it prevents an attacker from racing to register the reserved administrator name. Create the account over the private deployment URL or temporarily set the variable to `true`, register `Yun_Yan+baili20130209` with a strong password, then set it back to `false` and recreate the backend.

```bash
# after the admin has been created, leave this disabled
ADMIN_USERNAME_AUTO_PROMOTE=false
```

The username is configurable, but the default reserved administrator is exactly:

```text
Yun_Yan+baili20130209
```

## 5. Operations

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml restart
docker compose -f docker-compose.prod.yml pull
```

The `ide_data` volume contains the SQLite database and per-user workspaces. Back it up before upgrades:

```bash
docker run --rm -v python-ide_ide_data:/data -v "$PWD":/backup alpine tar czf /backup/ide-data.tgz -C /data .
```

## Important security boundary

This release isolates users' files and credentials, but Python and pip still execute inside one backend container. Do not expose it to untrusted users without adding per-job containers or a sandbox, CPU/memory quotas, process limits, network egress policy, package allowlisting, and rate limiting.
