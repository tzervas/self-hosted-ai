#!/usr/bin/env bash
# Reset PostgreSQL PVC for Bitnami Migration
# Deletes old PVC with incompatible permissions and allows fresh creation

set -euo pipefail

NAMESPACE="ai-services"
STATEFULSET="postgresql"
PVC="data-postgresql-0"

echo "========================================="
echo "PostgreSQL PVC Reset for Bitnami Migration"
echo "========================================="
echo ""
echo "This script will:"
echo "  1. Scale PostgreSQL StatefulSet to 0"
echo "  2. Delete the old PVC (contains incompatible data)"
echo "  3. Scale PostgreSQL back to 1"
echo "  4. Verify new pod starts with correct permissions"
echo ""
echo "⚠️  WARNING: This will delete all PostgreSQL data!"
echo "   (LiteLLM will recreate its schema automatically)"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Aborted."
  exit 1
fi

echo ""
echo "[1/5] Scaling PostgreSQL to 0 replicas..."
kubectl scale statefulset "$STATEFULSET" -n "$NAMESPACE" --replicas=0

echo "Waiting for pod to terminate..."
kubectl wait --for=delete pod/postgresql-0 -n "$NAMESPACE" --timeout=120s || true
sleep 5

echo ""
echo "[2/5] Deleting old PVC..."
kubectl delete pvc "$PVC" -n "$NAMESPACE"

echo "Waiting for PVC deletion..."
while kubectl get pvc "$PVC" -n "$NAMESPACE" &>/dev/null; do
  echo "  Still deleting..."
  sleep 3
done

echo ""
echo "[3/5] Scaling PostgreSQL to 1 replica..."
kubectl scale statefulset "$STATEFULSET" -n "$NAMESPACE" --replicas=1

echo ""
echo "[4/5] Waiting for new pod to be created..."
sleep 10

echo ""
echo "[5/5] Monitoring pod startup..."
echo ""

for i in {1..30}; do
  if kubectl get pod postgresql-0 -n "$NAMESPACE" &>/dev/null; then
    PHASE=$(kubectl get pod postgresql-0 -n "$NAMESPACE" -o jsonpath='{.status.phase}')
    READY=$(kubectl get pod postgresql-0 -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
    RESTARTS=$(kubectl get pod postgresql-0 -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].restartCount}')

    echo "[Attempt $i/30] Phase=$PHASE, Ready=$READY, Restarts=$RESTARTS"

    if [ "$READY" = "True" ]; then
      echo ""
      echo "✅ PostgreSQL is ready!"

      # Verify UID
      echo ""
      echo "Verifying rootless execution..."
      UID=$(kubectl exec postgresql-0 -n "$NAMESPACE" -- id -u)

      if [ "$UID" = "1001" ]; then
        echo "✅ Running as non-root UID $UID (Bitnami standard)"
      else
        echo "⚠️  WARNING: Running as UID $UID (expected 1001)"
      fi

      # Show logs
      echo ""
      echo "Recent logs:"
      kubectl logs postgresql-0 -n "$NAMESPACE" --tail=20

      echo ""
      echo "========================================="
      echo "✅ PostgreSQL Reset Complete!"
      echo "========================================="
      echo ""
      echo "Next steps:"
      echo "  1. Verify LiteLLM can connect:"
      echo "     kubectl logs -f deployment/litellm -n ai-services"
      echo ""
      echo "  2. Check database:"
      echo "     kubectl exec postgresql-0 -n ai-services -- psql -U litellm -c '\\l'"
      echo ""

      exit 0
    fi

    if [ "$RESTARTS" -gt 2 ]; then
      echo ""
      echo "❌ Pod is crash-looping. Showing logs:"
      kubectl logs postgresql-0 -n "$NAMESPACE" --tail=50
      echo ""
      echo "Check for persistent issues with: kubectl describe pod postgresql-0 -n $NAMESPACE"
      exit 1
    fi
  else
    echo "[Attempt $i/30] Waiting for pod to be created..."
  fi

  sleep 10
done

echo ""
echo "⚠️  Timeout waiting for PostgreSQL to become ready"
echo "Check status with: kubectl get pods -n $NAMESPACE"
echo "View logs with: kubectl logs postgresql-0 -n $NAMESPACE"
exit 1
