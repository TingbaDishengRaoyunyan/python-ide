# Server security baseline

Use a dedicated Ubuntu host or managed Kubernetes node. Enable unattended security updates, a host firewall allowing only SSH/80/443, SSH keys-only with root login disabled, disk encryption where available, least-privilege cloud IAM, time synchronization, and centralized logs.

Do not expose PostgreSQL, Redis, Prometheus, Grafana, the Kubernetes API, Docker socket, or runner service to the public internet. Rotate secrets, patch images, scan dependencies, and test backups regularly.

The Kubernetes runner should use Pod Security `restricted`, a non-root UID, `allowPrivilegeEscalation: false`, dropped capabilities, a read-only root filesystem, seccomp `RuntimeDefault`, no service-account token, and a sandbox runtime (gVisor/Kata) where available.
