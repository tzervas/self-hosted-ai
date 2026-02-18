#!/usr/bin/env bash
set -euo pipefail

# fix-remaining-apps.sh
# =====================
# One-time cluster cleanup to resolve remaining unhealthy ArgoCD apps.
# Run after PRs are merged to main and ArgoCD has picked up the changes.
#
# Root cause chain:
#   Longhorn backup-target bug → gitaly/minio volumes stuck → all GitLab
#   components in CrashLoopBackOff → shared-secrets never runs → runner
#   secrets missing → gitlab-runners degraded → bundled cert-manager RBAC
#   never pruned → cert-manager-issuers conflict
#
# Prometheus: monitoring quota at 8/8 CPU limits, admission job needs 1 CPU.
#   Quota increase committed (8→12), but stale job must be deleted first.
#
# Safe to run multiple times (idempotent).

echo "=== Step 1: Fix Longhorn volumes stuck due to backup-target bug ==="
echo "Longhorn v1.10 volume controller fails reconciliation when backup-target"
echo "label references an unconfigured BackupTarget (empty URL). Removing the"
echo "label unblocks volume provisioning. Existing attached volumes are unaffected."
echo ""

# Identify stuck volumes (have backup-target label but empty state)
STUCK_VOLUMES=$(kubectl get volume.longhorn.io -n longhorn-system \
  -o jsonpath='{range .items[?(@.status.state=="")]}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)

if [ -n "$STUCK_VOLUMES" ]; then
  echo "Found stuck volumes:"
  echo "$STUCK_VOLUMES"
  for vol in $STUCK_VOLUMES; do
    echo "  Removing backup-target label from $vol..."
    kubectl label volume.longhorn.io "$vol" -n longhorn-system backup-target- 2>/dev/null || true
    kubectl label volume.longhorn.io "$vol" -n longhorn-system recurring-job-group.longhorn.io/default- 2>/dev/null || true
  done
  echo "✓ Stuck volume labels removed — Longhorn should begin provisioning"
else
  echo "No stuck volumes found, skipping"
fi

echo ""
echo "=== Step 2: Clean stale Prometheus admission webhook resources ==="
echo "PreSync hook resources from a failed sync block all future syncs."
echo "The monitoring quota has been increased (8→12 CPU), but the stale"
echo "job must be deleted so ArgoCD can recreate it with the new quota."
kubectl delete job prometheus-kube-prometheus-admission-create -n monitoring --ignore-not-found
kubectl delete job prometheus-kube-prometheus-admission-patch -n monitoring --ignore-not-found
kubectl delete clusterrole prometheus-kube-prometheus-admission --ignore-not-found
kubectl delete clusterrolebinding prometheus-kube-prometheus-admission --ignore-not-found
kubectl delete role prometheus-kube-prometheus-admission -n monitoring --ignore-not-found
kubectl delete rolebinding prometheus-kube-prometheus-admission -n monitoring --ignore-not-found
kubectl delete serviceaccount prometheus-kube-prometheus-admission -n monitoring --ignore-not-found
echo "✓ Prometheus admission resources cleaned"

echo ""
echo "=== Step 3: Create gitlab-runner-certs secret ==="
echo "GitLab runner needs a certs secret for TLS verification."
echo "Creates empty placeholder until GitLab's shared-secrets job populates it."
kubectl create secret generic gitlab-runner-certs -n gitlab \
  --from-literal=ca.crt="" \
  --dry-run=client -o yaml | kubectl apply -f -
echo "✓ gitlab-runner-certs secret created"

echo ""
echo "=== Step 4: Restart stuck GitLab pods ==="
echo "After Longhorn volumes are provisioned, restart pods stuck in Init/CrashLoop."
# Delete pods in CrashLoopBackOff or Init state to force fresh scheduling
kubectl delete pods -n gitlab -l app=sidekiq --force --grace-period=0 2>/dev/null || true
kubectl delete pods -n gitlab -l app=webservice --force --grace-period=0 2>/dev/null || true
kubectl delete pods -n gitlab -l app=registry --force --grace-period=0 2>/dev/null || true
echo "✓ Stuck GitLab pods restarted"

echo ""
echo "=== Step 5: Trigger ArgoCD re-syncs ==="
# Sync resource-quotas first (provides headroom for prometheus)
argocd app sync resource-quotas --prune 2>/dev/null || echo "  resource-quotas sync triggered"
sleep 5
# Then prometheus (needs the quota headroom)
argocd app sync prometheus --force --prune 2>/dev/null || echo "  prometheus sync triggered"
# Then gitlab ecosystem
argocd app sync gitlab --prune 2>/dev/null || echo "  gitlab sync triggered"
argocd app sync gitlab-redis --prune 2>/dev/null || echo "  gitlab-redis sync triggered"
# Other OutOfSync apps
argocd app sync linkerd-crds --prune 2>/dev/null || echo "  linkerd-crds sync triggered"
argocd app sync cert-manager-issuers --prune 2>/dev/null || echo "  cert-manager-issuers sync triggered"
echo "✓ All syncs triggered"

echo ""
echo "=== Step 6: Wait and verify ==="
echo "Waiting 60 seconds for syncs to propagate..."
sleep 60
echo ""
echo "Current application status:"
kubectl get applications -n argocd \
  -o custom-columns='NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status' \
  | sort
echo ""

# Count remaining issues
ISSUES=$(kubectl get applications -n argocd -o json | python3 -c "
import sys, json
apps = json.load(sys.stdin)['items']
degraded = [a['metadata']['name'] for a in apps if a.get('status',{}).get('health',{}).get('status') == 'Degraded']
outofsync = [a['metadata']['name'] for a in apps if a.get('status',{}).get('sync',{}).get('status') == 'OutOfSync']
if degraded:
    print(f'Degraded ({len(degraded)}): {', '.join(degraded)}')
if outofsync:
    print(f'OutOfSync ({len(outofsync)}): {', '.join(outofsync)}')
if not degraded and not outofsync:
    print('All apps Synced and Healthy!')
" 2>/dev/null || echo "Could not parse app status")
echo "$ISSUES"
echo ""
echo "Note: Some apps may take 2-5 minutes to fully converge."
echo "  - GitLab: depends on gitaly volume provisioning (may take 1-2 min)"
echo "  - Prometheus: PreSync hooks must complete before main sync"
echo "  - tts-server: external dependency (Coqui model hosting) — may remain degraded"
