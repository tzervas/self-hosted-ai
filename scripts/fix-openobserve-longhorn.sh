#!/usr/bin/env bash
set -euo pipefail

# fix-openobserve-longhorn.sh
# Cleans up stuck Longhorn resources and restarts OpenObserve with emptyDir persistence.
#
# Root cause: Longhorn v1.10.x has a webhook that rejects ALL volume mutations when
# spec.backupTargetName is empty. Combined with StorageClass fromBackup:"" propagating
# empty values to volumes, this creates a deadlock: volumes can't provision, and you
# can't patch or delete them either.
#
# Fix: Temporarily disable the Longhorn webhook, clean up, fix StorageClasses, re-enable.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Trap to re-enable webhooks on exit (safety net)
WEBHOOKS_DISABLED=false
cleanup() {
    if [ "$WEBHOOKS_DISABLED" = true ]; then
        warn "Re-enabling Longhorn webhooks (cleanup handler)..."
        restore_webhooks
    fi
}
trap cleanup EXIT

# --- Webhook management ---
VALIDATOR_BACKUP=""
MUTATOR_BACKUP=""

disable_webhooks() {
    info "  Backing up and disabling Longhorn admission webhooks..."
    VALIDATOR_BACKUP=$(kubectl get validatingwebhookconfiguration longhorn-webhook-validator -o json 2>/dev/null)
    MUTATOR_BACKUP=$(kubectl get mutatingwebhookconfiguration longhorn-webhook-mutator -o json 2>/dev/null)

    kubectl delete validatingwebhookconfiguration longhorn-webhook-validator --wait=false 2>/dev/null || true
    kubectl delete mutatingwebhookconfiguration longhorn-webhook-mutator --wait=false 2>/dev/null || true
    WEBHOOKS_DISABLED=true
    sleep 2
    info "  Webhooks disabled."
}

restore_webhooks() {
    info "  Restoring Longhorn admission webhooks..."
    if [ -n "$VALIDATOR_BACKUP" ]; then
        echo "$VALIDATOR_BACKUP" | python3 -c '
import sys, json
data = json.load(sys.stdin)
# Clean metadata for recreation
for key in ["resourceVersion", "uid", "creationTimestamp", "managedFields"]:
    data["metadata"].pop(key, None)
json.dump(data, sys.stdout)
' | kubectl create -f - 2>/dev/null || warn "  Could not restore validator (Longhorn will recreate it)"
    fi
    if [ -n "$MUTATOR_BACKUP" ]; then
        echo "$MUTATOR_BACKUP" | python3 -c '
import sys, json
data = json.load(sys.stdin)
for key in ["resourceVersion", "uid", "creationTimestamp", "managedFields"]:
    data["metadata"].pop(key, None)
json.dump(data, sys.stdout)
' | kubectl create -f - 2>/dev/null || warn "  Could not restore mutator (Longhorn will recreate it)"
    fi
    WEBHOOKS_DISABLED=false
    info "  Webhooks restored."
}

# === STEP 1: Disable Longhorn webhooks ===
info "Step 1: Disabling Longhorn webhooks to allow volume cleanup..."
disable_webhooks

# === STEP 2: Clean up OpenObserve resources ===
info "Step 2: Cleaning up stuck OpenObserve resources..."

if kubectl get statefulset openobserve-openobserve-standalone -n monitoring &>/dev/null; then
    info "  Deleting StatefulSet..."
    kubectl delete statefulset openobserve-openobserve-standalone -n monitoring --wait=false || true
fi

for pod in $(kubectl get pods -n monitoring -l app.kubernetes.io/name=openobserve-standalone -o name 2>/dev/null); do
    warn "  Force-deleting pod: $pod"
    kubectl delete "$pod" -n monitoring --force --grace-period=0 || true
done

if kubectl get pvc data-openobserve-openobserve-standalone-0 -n monitoring &>/dev/null; then
    info "  Removing PVC finalizer and deleting..."
    kubectl patch pvc data-openobserve-openobserve-standalone-0 -n monitoring \
        -p '{"metadata":{"finalizers":null}}' --type=merge 2>/dev/null || true
    kubectl delete pvc data-openobserve-openobserve-standalone-0 -n monitoring --wait=false 2>/dev/null || true
fi

# === STEP 3: Clean up ALL stuck Longhorn volumes ===
info "Step 3: Cleaning up stuck Longhorn volumes..."

STUCK_VOLS=$(kubectl get volumes.longhorn.io -n longhorn-system -o json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data.get('items', []):
    state = item.get('status', {}).get('state', '')
    if state in ('', 'deleting'):
        print(item['metadata']['name'])
" 2>/dev/null || true)

if [ -n "$STUCK_VOLS" ]; then
    for vol in $STUCK_VOLS; do
        warn "  Cleaning up volume: $vol"
        # Remove finalizer from volume
        kubectl patch volumes.longhorn.io "$vol" -n longhorn-system \
            -p '{"metadata":{"finalizers":null}}' --type=merge 2>/dev/null || true
        # Remove finalizers from replicas
        for replica in $(kubectl get replicas.longhorn.io -n longhorn-system -o name 2>/dev/null | grep "${vol}" || true); do
            kubectl patch "$replica" -n longhorn-system \
                -p '{"metadata":{"finalizers":null}}' --type=merge 2>/dev/null || true
        done
        # Remove finalizers from engines
        for engine in $(kubectl get engines.longhorn.io -n longhorn-system -o name 2>/dev/null | grep "${vol}" || true); do
            kubectl patch "$engine" -n longhorn-system \
                -p '{"metadata":{"finalizers":null}}' --type=merge 2>/dev/null || true
        done
        # Delete the volume
        kubectl delete volumes.longhorn.io "$vol" -n longhorn-system --wait=false 2>/dev/null || true
    done
    info "  Cleaned up $(echo "$STUCK_VOLS" | wc -l) stuck volumes."
else
    info "  No stuck volumes found."
fi

# Clean up orphaned PVs pointing to deleted volumes
for pv in $(kubectl get pv -o json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data.get('items', []):
    phase = item.get('status', {}).get('phase', '')
    driver = item.get('spec', {}).get('csi', {}).get('driver', '')
    if phase in ('Released', 'Failed') and driver == 'driver.longhorn.io':
        print(item['metadata']['name'])
" 2>/dev/null || true); do
    warn "  Deleting orphaned PV: $pv"
    kubectl delete pv "$pv" --wait=false 2>/dev/null || true
done

# === STEP 4: Fix StorageClasses (WHILE WEBHOOKS ARE STILL DISABLED) ===
# This must happen before re-enabling webhooks, because the webhook validates
# volumes against StorageClass params. If SCs still have fromBackup:"", the
# webhook will reject all volume operations after re-enable.
info "Step 4: Fixing StorageClasses (webhooks still disabled)..."

for sc_name in longhorn-homelab longhorn longhorn-single; do
    if ! kubectl get storageclass "$sc_name" &>/dev/null; then
        info "  StorageClass $sc_name not found, skipping."
        continue
    fi

    info "  Fixing $sc_name..."
    kubectl get storageclass "$sc_name" -o json | python3 -c "
import sys, json
sc = json.load(sys.stdin)
name = sc['metadata']['name']

# Remove the fromBackup antipattern (causes v1.10.x webhook deadlock)
sc['parameters'].pop('fromBackup', None)

# Fix the default 'longhorn' SC: reduce replicas, demote from default
if name == 'longhorn':
    sc['parameters']['numberOfReplicas'] = '1'
    sc['parameters']['dataLocality'] = 'best-effort'
    sc['metadata'].setdefault('annotations', {})['storageclass.kubernetes.io/is-default-class'] = 'false'

# Ensure longhorn-homelab IS the default
if name == 'longhorn-homelab':
    sc['metadata'].setdefault('annotations', {})['storageclass.kubernetes.io/is-default-class'] = 'true'

# Clean metadata for replace
for key in ['resourceVersion', 'uid', 'creationTimestamp', 'managedFields']:
    sc['metadata'].pop(key, None)
sc['metadata'].get('annotations', {}).pop('kubectl.kubernetes.io/last-applied-configuration', None)
json.dump(sc, sys.stdout)
" | kubectl replace -f - 2>/dev/null || warn "  Could not replace $sc_name"
done

# Delete redundant longhorn-single SC (duplicate of longhorn-homelab)
if kubectl get storageclass longhorn-single &>/dev/null; then
    warn "  Deleting redundant StorageClass: longhorn-single"
    kubectl delete storageclass longhorn-single 2>/dev/null || true
fi

# Delete stale weekly-backup RecurringJob (no backup target configured)
if kubectl get recurringjobs.longhorn.io weekly-backup -n longhorn-system &>/dev/null; then
    warn "  Deleting weekly-backup RecurringJob (no backup target configured)"
    kubectl delete recurringjobs.longhorn.io weekly-backup -n longhorn-system 2>/dev/null || true
fi

# === STEP 5: Clean up evicted Longhorn pods ===
info "Step 5: Cleaning up evicted Longhorn pods..."

for pod in $(kubectl get pods -n longhorn-system --field-selector=status.phase=Failed -o name 2>/dev/null); do
    warn "  Deleting: $pod"
    kubectl delete "$pod" -n longhorn-system || true
done

# === STEP 6: Re-enable Longhorn webhooks ===
info "Step 6: Re-enabling Longhorn webhooks..."
restore_webhooks
sleep 5  # Give webhooks time to register

# === STEP 7: Clean up OpenObserve again (in case ArgoCD recreated with old SC) ===
info "Step 7: Ensuring OpenObserve is clean before final sync..."

if kubectl get statefulset openobserve-openobserve-standalone -n monitoring &>/dev/null; then
    kubectl delete statefulset openobserve-openobserve-standalone -n monitoring --wait=false 2>/dev/null || true
fi
for pod in $(kubectl get pods -n monitoring -l app.kubernetes.io/name=openobserve-standalone -o name 2>/dev/null); do
    kubectl delete "$pod" -n monitoring --force --grace-period=0 2>/dev/null || true
done
if kubectl get pvc data-openobserve-openobserve-standalone-0 -n monitoring &>/dev/null; then
    kubectl patch pvc data-openobserve-openobserve-standalone-0 -n monitoring \
        -p '{"metadata":{"finalizers":null}}' --type=merge 2>/dev/null || true
    kubectl delete pvc data-openobserve-openobserve-standalone-0 -n monitoring --wait=false 2>/dev/null || true
fi

# === STEP 8: Trigger ArgoCD sync ===
info "Step 8: Triggering ArgoCD sync for OpenObserve..."

kubectl patch application openobserve -n argocd --type merge \
    -p '{"operation":{"sync":{"revision":"HEAD"}}}' 2>/dev/null || \
    warn "  Could not trigger sync (may already be syncing)"

# === STEP 9: Wait for OpenObserve ===
info "Step 9: Waiting for OpenObserve to become ready (timeout: 180s)..."

TIMEOUT=180
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    STATUS=$(kubectl get pods -n monitoring -l app.kubernetes.io/name=openobserve-standalone \
        -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")
    READY=$(kubectl get pods -n monitoring -l app.kubernetes.io/name=openobserve-standalone \
        -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || echo "false")

    if [ "$STATUS" = "Running" ] && [ "$READY" = "true" ]; then
        echo
        info "OpenObserve is Running and Ready!"
        break
    fi

    echo -ne "\r  Waiting... ${ELAPSED}s (status: ${STATUS}, ready: ${READY})  "
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done
echo

if [ $ELAPSED -ge $TIMEOUT ]; then
    error "OpenObserve did not become ready within ${TIMEOUT}s"
    warn "Check: kubectl get pods -n monitoring | grep openobserve"
    warn "Check: kubectl describe pod -n monitoring -l app.kubernetes.io/name=openobserve-standalone"
    exit 1
fi

# === STEP 10: Verify ===
info "Step 10: Final verification..."
echo
echo "=== OpenObserve Pod ==="
kubectl get pods -n monitoring -l app.kubernetes.io/name=openobserve-standalone -o wide 2>/dev/null
echo
echo "=== All Observability Services ==="
for app in ingress-redirects otel-collector tempo openobserve; do
    HEALTH=$(kubectl get application "$app" -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null || echo "N/A")
    SYNC=$(kubectl get application "$app" -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "N/A")
    printf "  %-25s Health: %-12s Sync: %s\n" "$app" "$HEALTH" "$SYNC"
done
echo
echo "=== Longhorn Health ==="
kubectl get volumes.longhorn.io -n longhorn-system -o custom-columns='NAME:.metadata.name,STATE:.status.state,ROBUSTNESS:.status.robustness' 2>/dev/null
echo
info "Done! OpenObserve: https://logs.vectorweight.com"
