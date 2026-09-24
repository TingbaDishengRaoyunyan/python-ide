# Production cloud deployment template

This directory is the production baseline for a public multi-tenant deployment. It deliberately separates the control plane from code execution:

```text
Internet -> Caddy/TLS -> frontend -> API/control plane -> runner
                                      |             |
                                      |             +-- disposable Kubernetes Job
                                      +-- PostgreSQL/Redis/object storage (replace dev volumes)
```

## Required production controls

- **Tenant isolation:** every request is authorized by tenant/user membership; never accept a workspace path from the client as an authorization decision.
- **Per-execution isolation:** create one short-lived Job/Pod per run; do not execute untrusted code in the API container.
- **Network egress:** runner Pods use the default-deny NetworkPolicy and only an explicit package mirror/API allowlist.
- **Resources:** namespace quotas plus per-job CPU, memory, PID and timeout limits.
- **Packages:** use the internal package proxy and allowlist package names/versions for public tenants.
- **Audit:** append authentication, permission, package, run and admin events to an append-only sink.
- **TLS/domain:** Caddy obtains certificates only after DNS and ports 80/443 are configured.

The Compose file is suitable for a single-server control-plane deployment. The Kubernetes manifests are the recommended execution boundary for untrusted public workloads.
