# Manual Cleanup Tasks

Tasks that require manual intervention or elevated permissions.

## 1. Remove Orphaned qemu-binfmt ArgoCD Application

**Status**: Pending Manual Action
**Priority**: Low (non-blocking, failing for 22 days without impact)
**Date Identified**: 2026-02-07

### Issue

The `qemu-binfmt` ArgoCD application exists in the cluster but its source (`helm/qemu-binfmt`) has been removed from the repository. The pods are in permanent CrashLoopBackOff due to `/proc/sys/fs/binfmt_misc` mount restrictions.

### Pods Affected

```
kube-system/qemu-binfmt-jw7cj    - 105 restarts (8h)
kube-system/qemu-binfmt-pbst4    - 4153 restarts (22d)
```

### Error

```
error mounting "/proc/sys/fs/binfmt_misc" to rootfs: cannot be mounted because it is inside /proc
```

### Why It Can Be Removed

- **Not Needed**: Actions Runner Controller (ARC) handles cross-platform builds
- **Failing**: Init container can't mount `/proc/sys/fs/binfmt_misc` due to security restrictions
- **No Impact**: Has been failing for 22 days without affecting any services
- **Stale**: Source files removed from repository

### Cleanup Command

```bash
# Delete the ArgoCD application
kubectl delete application qemu-binfmt -n argocd

# Verify pods are cleaned up
kubectl get pods -n kube-system | grep qemu-binfmt

# Delete DaemonSet if still exists
kubectl delete daemonset qemu-binfmt -n kube-system
```

### Post-Cleanup Verification

```bash
# Should return no results
kubectl get application qemu-binfmt -n argocd
kubectl get daemonset qemu-binfmt -n kube-system
kubectl get pods -n kube-system | grep qemu-binfmt
```

---

## 2. Remove Orphaned LiteLLM Service from Default Namespace

**Status**: Pending Manual Action
**Priority**: Low (non-blocking, orphaned service)
**Date Identified**: 2026-02-07

### Issue

Duplicate LiteLLM service exists in `default` namespace (22d old) while the active service is in `ai-services` namespace (10d old). The default namespace service has no associated deployment or pods - it's an orphaned resource.

### Services

```
default/litellm         - 22d old (ClusterIP: 10.43.240.186) [ORPHANED]
ai-services/litellm     - 10d old (ClusterIP: 10.43.154.137) [ACTIVE]
```

### Why It Can Be Removed

- **No Backend**: No deployment or pods in default namespace
- **Duplicate**: Active LiteLLM runs in ai-services namespace
- **Stale**: 22 days old vs 10 days for current deployment
- **No Traffic**: Nothing routes to this service

### Cleanup Command

```bash
# Delete the orphaned service
kubectl delete service litellm -n default

# Verify only ai-services instance remains
kubectl get services --all-namespaces | grep litellm
```

### Post-Cleanup Verification

```bash
# Should show only ai-services/litellm
kubectl get services litellm -A
```

---

## Future Tasks

Additional manual cleanup tasks will be documented here as they are identified.
