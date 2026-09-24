# Tenant, worker, GPU and user-management deployment

This release adds per-user tenant workspaces, a private execution worker, role/permission administration, user search, and a GPU runtime profile.

## Launch

```bash
cp deploy/.env.production.example .env
# set SESSION_SECRET, WORKER_TOKEN and DOMAIN
deploy/publish.sh
```

The admin panel searches users by username as you type. Administrators can set roles and individual permissions: `ide`, `run`, `pip`, `gpu`, `manage_users`, and `manage_roles`.

## GPU

`runtimes/gpu/Dockerfile` and `docker-compose.gpu.yml` provide a CUDA/PyTorch smoke-test profile. Install NVIDIA drivers and NVIDIA Container Toolkit first. A production GPU scheduler should assign GPUs per job; this profile does not automatically grant hardware access to users.

## Security boundary

The worker is private, non-root, read-only, drops capabilities, limits memory/CPU/PIDs, and has execution timeouts. This is stronger isolation than running code in the API, but it is not a perfect hostile-code sandbox because the worker receives workspace access and pip has network access. For hostile public workloads, add disposable per-job containers/VMs, network egress policy, seccomp/AppArmor, package allowlists and rate limits.
