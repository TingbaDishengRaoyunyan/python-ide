# Kubernetes execution boundary

The runner must create a disposable Job for every run. The API must pass a server-side tenant ID and a short-lived signed job token; never trust a client-supplied tenant path. The Job should mount only a temporary copy of the project, use a non-root UID, and be deleted after completion.

Apply the baseline controls:

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/resourcequota.yaml
kubectl apply -f deploy/k8s/networkpolicy.yaml
kubectl apply -f deploy/k8s/runner-serviceaccount.yaml
```

For stronger isolation use a sandboxed runtime class such as gVisor or Kata Containers and set `RUNNER_RUNTIME_CLASS` in the runner deployment. Do not mount `/var/run/docker.sock` into the API or runner.
