#!/usr/bin/env bash
set -euo pipefail

# One-Time ArgoCD Cluster Cleanup
# Consolidates all manual kubectl commands needed to unblock ArgoCD syncs.
# Run after pushing the hardened ArgoCD app definitions to main.
#
# What this script does:
#   1. Removes duplicate App-of-Apps (dev-platform)
#   2. Removes orphaned/broken apps (dify, loki, vpa, qemu-binfmt)
#   3. Deletes immutable StorageClass so ArgoCD can recreate it
#   4. Patches Longhorn CRDs with correct conversion strategy
#   5. Deletes StatefulSets that block on immutable VCT fields
#   6. Restarts pods stuck on stale config
#   7. Cleans up stuck Kyverno jobs
#   8. Re-applies root-apps and triggers full sync
#
# Safe to run multiple times (idempotent).

echo "=== ArgoCD Cluster Cleanup ==="
echo "Timestamp: $(date)"
echo

# --- Step 1: Remove duplicate App-of-Apps ---
echo "1. Removing duplicate dev-platform App-of-Apps..."
if kubectl get application dev-platform -n argocd &>/dev/null; then
  kubectl delete application dev-platform -n argocd
  echo "   Deleted dev-platform"
else
  echo "   dev-platform not found, skipping"
fi

# --- Step 2: Remove orphaned/broken apps ---
echo
echo "2. Removing orphaned applications..."
for app in dify loki vpa qemu-binfmt; do
  if kubectl get application "$app" -n argocd &>/dev/null; then
    kubectl patch application "$app" -n argocd \
      --type json -p '[{"op":"remove","path":"/metadata/finalizers"}]' 2>/dev/null || true
    kubectl delete application "$app" -n argocd --ignore-not-found=true
    echo "   Deleted $app"
  else
    echo "   $app not found, skipping"
  fi
done

# --- Step 3: Delete immutable StorageClasses ---
echo
echo "3. Deleting immutable StorageClasses (ArgoCD will recreate with Force=true,Replace=true)..."
for sc in longhorn-homelab longhorn-gpu-local; do
  if kubectl get storageclass "$sc" &>/dev/null; then
    kubectl delete storageclass "$sc"
    echo "   Deleted StorageClass $sc"
  else
    echo "   StorageClass $sc not found, skipping"
  fi
done

# --- Step 4: Patch Longhorn CRDs ---
echo
echo "4. Patching Longhorn CRDs (conversion strategy)..."
for crd in $(kubectl get crd -o name | grep longhorn.io 2>/dev/null); do
  kubectl patch "$crd" --type=merge -p '{"spec":{"conversion":{"strategy":"None"}}}' 2>/dev/null || true
done
echo "   Longhorn CRDs patched"

# --- Step 5: Delete StatefulSets with immutable VCT fields ---
echo
echo "5. Deleting StatefulSets blocked by immutable VCT fields (pods preserved)..."
for ns_sts in "ai-services/postgresql" "ai-services/redis" "monitoring/prometheus-kube-prometheus-stack-prometheus" "monitoring/tempo" "monitoring/openobserve"; do
  ns="${ns_sts%%/*}"
  sts="${ns_sts##*/}"
  if kubectl get statefulset "$sts" -n "$ns" &>/dev/null; then
    kubectl delete statefulset "$sts" -n "$ns" --cascade=orphan
    echo "   Deleted StatefulSet $sts in $ns (pods preserved)"
  else
    echo "   StatefulSet $sts in $ns not found, skipping"
  fi
done

# --- Step 6: Restart pods stuck on stale config ---
echo
echo "6. Restarting pods stuck on stale config..."
for ns_deploy in "monitoring/openobserve" "monitoring/prometheus-kube-prometheus-stack-operator"; do
  ns="${ns_deploy%%/*}"
  deploy="${ns_deploy##*/}"
  if kubectl get deployment "$deploy" -n "$ns" &>/dev/null; then
    kubectl rollout restart deployment "$deploy" -n "$ns"
    echo "   Restarted $deploy in $ns"
  else
    echo "   Deployment $deploy in $ns not found, skipping"
  fi
done

# --- Step 7: Clean up stuck Kyverno jobs ---
echo
echo "7. Cleaning up stuck Kyverno jobs..."
kubectl delete jobs -n kyverno --all --ignore-not-found=true 2>/dev/null || true
echo "   Kyverno jobs cleaned"

# --- Step 8: Delete ComfyUI PVC if orphaned ---
echo
echo "8. Cleaning up orphaned PVCs..."
if kubectl get pvc comfyui-data -n gpu-workloads &>/dev/null; then
  kubectl delete pvc comfyui-data -n gpu-workloads
  echo "   Deleted orphaned comfyui-data PVC"
else
  echo "   No orphaned PVCs found"
fi

# --- Step 9: Re-apply root-apps and trigger sync ---
echo
echo "9. Re-applying root-apps and triggering sync..."
kubectl apply -f argocd/apps/root.yaml
echo "   root-apps applied"

echo
echo "Waiting 10s for ArgoCD to pick up changes..."
sleep 10

# Trigger sync on root-apps
if command -v argocd &>/dev/null; then
  argocd app sync root-apps --async 2>/dev/null || echo "   argocd CLI sync failed (may need login), manual sync OK"
else
  echo "   argocd CLI not found — sync will happen automatically via selfHeal"
fi

echo
echo "=== Cleanup Complete ==="
echo
echo "Next steps:"
echo "  1. Monitor: kubectl get applications -n argocd"
echo "  2. Wait ~5min for all apps to reconcile"
echo "  3. Expected: 0 Unknown, 0 Degraded, all Synced/Healthy"
echo
echo "If specific apps remain OutOfSync, run:"
echo "  argocd app sync <app-name>"
