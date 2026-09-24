# UI, sandbox, and GPU upgrade

The UI now includes IDE and admin tabs. Administrators can view counts, list users, change roles, and delete users. The default reserved admin username is `Yun_Yan+baili20130209`.

## One-command launch

```bash
chmod +x deploy/up.sh
./deploy/up.sh
```

For the CUDA smoke-test runtime:

```bash
./deploy/up.sh gpu
```

GPU requirements: NVIDIA driver, Docker Engine, and NVIDIA Container Toolkit. The GPU profile installs PyTorch CUDA 12.4 into a dedicated runtime image; it is a validation/runtime profile, not yet a per-user GPU scheduler.

## Stronger sandbox boundary

The production compose file uses a read-only application filesystem, a non-root backend image, an init process, a private network, a persistent data volume, and execution timeouts. This is defense-in-depth, not a complete hostile-code sandbox: user Python still runs in the backend container.

For untrusted public users, deploy execution as a separate worker service with one disposable container per run, no Docker socket exposed to the API, CPU/memory/PID limits, a restricted egress network, read-only root filesystem, and an allowlisted package mirror. Do not claim this MVP is safe for arbitrary hostile code until that worker boundary is implemented.
