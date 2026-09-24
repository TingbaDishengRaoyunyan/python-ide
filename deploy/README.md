# Production deployment guide

## Prerequisites

- Docker Engine with Compose
- Public domain and DNS records for `DOMAIN`
- Open ports 80 and 443 on the server
- A host firewall with only required ingress
- A secure secrets store or `.env` file outside version control

## Launch

```bash
cp deploy/.env.production.example .env
# edit the values in .env
chmod +x deploy/publish-production.sh
./deploy/publish-production.sh
```

## Bootstrap admin

The reserved administrator is:

```text
Yun_Yan+baili20130209
```

Keep `ADMIN_AUTO_PROMOTE=false` unless you are intentionally registering the reserved account in a private bootstrap environment.

## Production guardrails

- Do not expose Postgres, Redis, Grafana or the worker directly to the internet.
- Use default-deny egress for runner workloads.
- Use a package mirror or allowlist for pip installs.
- Back up `/data` volumes and secrets regularly.
- Rotate `SESSION_SECRET`, `WORKER_TOKEN`, and database credentials on a schedule.
- Add centralized logging and retention policies.
