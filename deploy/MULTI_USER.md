# Multi-user deployment

This version adds registration, login, signed sessions, role-based admin permissions, and an isolated persistent workspace for every user.

## Admin account

The requested username is configured as the administrator by default:

```text
Yun_Yan+baili20130209
```

It receives the `admin` role when registered. The password is **not stored in the repository**; the person registering the account must choose it. To change the reserved name, set `ADMIN_USERNAME` in `.env`.

> Security warning: if `ADMIN_USERNAME_AUTO_PROMOTE=true`, anyone who registers that exact username before the legitimate owner can claim admin. For a real public deployment, register this account first with a strong password, or set `ADMIN_USERNAME_AUTO_PROMOTE=false` and implement a private bootstrap process.

## Start

```bash
cp .env.example .env
# Set a random SESSION_SECRET in .env
docker compose -f docker-compose.prod.yml up -d --build
```

Every account gets its own workspace and `.venv`. Files and pip-installed packages are not shared between accounts. Admin APIs include user listing and deleting users; the UI currently exposes the normal IDE to all authenticated users.

## Important production limitation

This is an authenticated multi-user MVP, not yet a hostile-code sandbox. Python scripts and pip packages run inside the backend container. Before allowing unknown public users, add per-execution containers, CPU/memory/time limits, outbound-network policy, rate limiting, and an external identity provider.
