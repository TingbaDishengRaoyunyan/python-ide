# Production deployment baseline for this IDE

This project is now structured as a production control plane plus a dedicated execution worker.

## High-level architecture

- `frontend/` serves the IDE and admin UI.
- `backend/` hosts the control plane, auth, tenant permissions, and file APIs.
- `worker/` executes user code and pip installs in a separate service.
- `deploy/` contains the public deployment automation and TLS config.

## Core operational model

- User accounts are stored in SQLite for the control plane and are subject to role + permission checks.
- Files and workspaces are isolated by a username-derived workspace path.
- The API calls the worker for script execution and pip installs.
- Tests for service health and runner connectivity are configured in the deployment files.
- The default owner/admin username is `Yun_Yan+baili20130209`.

## Runtime requirements

For the public cloud deployment template:

- Docker Engine / Docker Compose
- Public domain and DNS records
- TLS-managed reverse proxy (Caddy)
- Postgres + Redis for production state
- Separate runner isolation for every trusted/public execution job
- Package mirror / allowlisted package sources

## Launch

```bash
chmod +x deploy/publish-production.sh
./deploy/publish-production.sh
```

Then review values in `.env` and the Caddy config before exposing the service publicly.

## Security limits

This is a strong control-plane baseline, but for hostile public workloads it must be expanded to:

- one disposable Job/VM per execution,
- default-deny network egress,
- CPU/memory/PID/time limits,
- seccomp/AppArmor or gVisor/Kata runtime,
- allowlisted package sources,
- append-only audit logs,
- backups and secret rotation.
