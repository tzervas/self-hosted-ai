#!/usr/bin/env bash
set -euo pipefail

# Fix ArgoCD Sync Issues
# Addresses CRD annotation limits and StatefulSet immutability errors

echo "=== ArgoCD Sync Issue Remediation ==="
echo "Timestamp: $(date)"
echo

# Issue 1: Prometheus CRDs - annotation size >262KB
echo "1. Fixing Prometheus CRD annotation size issues..."
kubectl delete crd prometheusagents.monitoring.coreos.com --ignore-not-found=true
kubectl delete crd prometheuses.monitoring.coreos.com --ignore-not-found=true
kubectl delete crd scrapeconfigs.monitoring.coreos.com --ignore-not-found=true
kubectl delete crd alertmanagerconfigs.monitoring.coreos.com --ignore-not-found=true
kubectl delete crd alertmanagers.monitoring.coreos.com --ignore-not-found=true
kubectl delete crd thanosrulers.monitoring.coreos.com --ignore-not-found=true
echo "✓ Prometheus CRDs deleted"

# Issue 2: ARC Controller CRDs - annotation size >262KB
echo
echo "2. Fixing ARC Controller CRD annotation size..."
kubectl delete crd autoscalingrunnersets.actions.github.com --ignore-not-found=true
kubectl delete crd ephemeralrunners.actions.github.com --ignore-not-found=true
kubectl delete crd ephemeralrunnersets.actions.github.com --ignore-not-found=true
echo "✓ ARC CRDs deleted"

# Issue 3: Gateway API CRDs - storage version conflicts
echo
echo "3. Fixing Gateway API CRD storage version conflicts..."
kubectl delete crd httproutes.gateway.networking.k8s.io --ignore-not-found=true
kubectl delete crd grpcroutes.gateway.networking.k8s.io --ignore-not-found=true
echo "✓ Gateway API CRDs deleted"

# Issue 4: PostgreSQL StatefulSet - immutable field errors
echo
echo "4. Recreating PostgreSQL StatefulSet..."
if kubectl get statefulset postgresql -n ai-services &>/dev/null; then
    kubectl delete statefulset postgresql -n ai-services --cascade=orphan
    echo "✓ PostgreSQL StatefulSet deleted (pods preserved)"
else
    echo "  PostgreSQL StatefulSet not found, skipping"
fi

# Issue 5: Redis StatefulSet - immutable field errors
echo
echo "5. Recreating Redis StatefulSet..."
if kubectl get statefulset redis -n ai-services &>/dev/null; then
    kubectl delete statefulset redis -n ai-services --cascade=orphan
    echo "✓ Redis StatefulSet deleted (pods preserved)"
else
    echo "  Redis StatefulSet not found, skipping"
fi

echo
echo "=== Remediation Complete ==="
echo "Next steps:"
echo "1. Wait 30s for CRD cleanup to complete"
echo "2. ArgoCD will automatically re-sync and recreate resources"
echo "3. Monitor with: kubectl get applications -n argocd"
echo
echo "Expected result: OutOfSync apps will transition to Synced/Healthy"
