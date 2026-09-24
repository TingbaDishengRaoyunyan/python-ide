# Production runbook and checklist

## Before launch

- [ ] Domain A/AAAA records point to the server; ports 80/443 are restricted to required ingress.
- [ ] `.env` is outside Git, has random secrets, and backups are encrypted.
- [ ] PostgreSQL is used for production state; SQLite is not used for shared tenants.
- [ ] Redis is private and password-protected.
- [ ] Caddy certificate issuance succeeds and renewal is tested.
- [ ] Owner `Yun_Yan+baili20130209` is bootstrapped privately with a strong password; `ADMIN_AUTO_PROMOTE=false`.
- [ ] Default-deny runner NetworkPolicy is applied.
- [ ] Per-job CPU, memory, PID and wall-clock limits are enforced.
- [ ] Package installs use an internal mirror/proxy and allowlist.
- [ ] Audit events are shipped to append-only storage with retention.
- [ ] Prometheus/Grafana are private or separately authenticated.
- [ ] Host firewall, automatic security updates, SSH keys-only, and Docker daemon protections are enabled.
- [ ] Backups have been restored successfully in a staging environment.

## Incident response

1. Disable new runs and package installs.
2. Revoke affected sessions and rotate `SESSION_SECRET`/worker credentials.
3. Preserve API, runner, Caddy and audit logs.
4. Isolate the affected tenant and destroy active runner Jobs.
5. Rotate package mirror credentials and inspect egress logs.
6. Restore only from a verified backup and document the incident.
