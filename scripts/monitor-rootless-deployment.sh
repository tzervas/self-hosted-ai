#!/usr/bin/env bash
# Rootless Deployment Monitor with Automated Rollback
# Monitors ArgoCD sync, pod health, and automatically rolls back on failure
set -euo pipefail

# Configuration
NAMESPACE="ai-services"
APPS=("postgresql" "redis")
BACKUP_DIR="/tmp/rootless-deployment-backup-$(date +%Y%m%d-%H%M%S)"
LOG_FILE="/tmp/rootless-deployment-monitor-$(date +%Y%m%d-%H%M%S).log"
MONITORING_DURATION=600  # 10 minutes max
CHECK_INTERVAL=10        # Check every 10 seconds
ROLLBACK_THRESHOLD=3     # Rollback after 3 consecutive failures

mkdir -p "$BACKUP_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status tracking
declare -A APP_STATUS
declare -A APP_FAILURES
declare -A APP_ROLLBACK_NEEDED

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $*"
}

success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $*${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $*${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $*${NC}"
}

header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║$(printf " %-66s" "$1")║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Backup current state
backup_current_state() {
    local app=$1
    log "Backing up current state of $app..."

    kubectl get statefulset "$app" -n "$NAMESPACE" -o yaml > "$BACKUP_DIR/${app}-statefulset-before.yaml" 2>/dev/null || true
    kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name="$app" -o yaml > "$BACKUP_DIR/${app}-pods-before.yaml" 2>/dev/null || true
    kubectl get application "$app" -n argocd -o yaml > "$BACKUP_DIR/${app}-argocd-app-before.yaml" 2>/dev/null || true

    success "Backup saved to $BACKUP_DIR/${app}-*-before.yaml"
}

# Check ArgoCD sync status
check_argocd_sync() {
    local app=$1
    local sync_status=$(kubectl get application "$app" -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")
    local health_status=$(kubectl get application "$app" -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown")

    echo "$sync_status:$health_status"
}

# Check StatefulSet status
check_statefulset_status() {
    local app=$1

    if ! kubectl get statefulset "$app" -n "$NAMESPACE" >/dev/null 2>&1; then
        echo "NotFound:0:0"
        return
    fi

    local ready=$(kubectl get statefulset "$app" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    local desired=$(kubectl get statefulset "$app" -n "$NAMESPACE" -o jsonpath='{.status.replicas}' 2>/dev/null || echo "0")
    local updated=$(kubectl get statefulset "$app" -n "$NAMESPACE" -o jsonpath='{.status.updatedReplicas}' 2>/dev/null || echo "0")
    local image=$(kubectl get statefulset "$app" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "unknown")

    echo "$image:$ready:$desired:$updated"
}

# Check pod health
check_pod_health() {
    local app=$1
    local pod_name="${app}-0"

    if ! kubectl get pod "$pod_name" -n "$NAMESPACE" >/dev/null 2>&1; then
        echo "NotFound"
        return
    fi

    local phase=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
    local ready=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
    local restarts=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo "0")

    echo "$phase:$ready:$restarts"
}

# Verify rootless execution
verify_rootless() {
    local app=$1
    local pod_name="${app}-0"

    if ! kubectl get pod "$pod_name" -n "$NAMESPACE" >/dev/null 2>&1; then
        echo "NotFound"
        return
    fi

    local uid=$(kubectl exec "$pod_name" -n "$NAMESPACE" -- id -u 2>/dev/null || echo "failed")
    echo "$uid"
}

# Automated rollback
perform_rollback() {
    local app=$1

    error "INITIATING AUTOMATED ROLLBACK FOR $app"

    # Check if backup exists
    if [ ! -f "$BACKUP_DIR/${app}-statefulset-before.yaml" ]; then
        error "No backup found for $app, cannot rollback automatically"
        return 1
    fi

    log "Scaling $app to 0..."
    kubectl scale statefulset "$app" -n "$NAMESPACE" --replicas=0 || true
    sleep 10

    log "Restoring previous StatefulSet configuration..."
    kubectl apply -f "$BACKUP_DIR/${app}-statefulset-before.yaml" || {
        error "Failed to restore $app configuration"
        return 1
    }

    log "Scaling $app back to 1..."
    kubectl scale statefulset "$app" -n "$NAMESPACE" --replicas=1 || true

    success "Rollback complete for $app"
    return 0
}

# Monitor single application
monitor_app() {
    local app=$1
    local elapsed=0

    APP_FAILURES[$app]=0
    APP_ROLLBACK_NEEDED[$app]=0

    while [ $elapsed -lt $MONITORING_DURATION ]; do
        # ArgoCD sync status
        local argocd_status=$(check_argocd_sync "$app")
        local sync_status=$(echo "$argocd_status" | cut -d: -f1)
        local health_status=$(echo "$argocd_status" | cut -d: -f2)

        # StatefulSet status
        local sts_status=$(check_statefulset_status "$app")
        local image=$(echo "$sts_status" | cut -d: -f1)
        local ready=$(echo "$sts_status" | cut -d: -f2)
        local desired=$(echo "$sts_status" | cut -d: -f3)
        local updated=$(echo "$sts_status" | cut -d: -f4)

        # Pod health
        local pod_health=$(check_pod_health "$app")
        local phase=$(echo "$pod_health" | cut -d: -f1)
        local pod_ready=$(echo "$pod_health" | cut -d: -f2)
        local restarts=$(echo "$pod_health" | cut -d: -f3)

        # Display status
        log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log "App: $app | Time: ${elapsed}s / ${MONITORING_DURATION}s"
        log "ArgoCD: Sync=$sync_status, Health=$health_status"
        log "StatefulSet: Image=$(basename "$image"), Ready=$ready/$desired, Updated=$updated"
        log "Pod: Phase=$phase, Ready=$pod_ready, Restarts=$restarts"

        # Check if using Bitnami image
        if [[ "$image" =~ "bitnami" ]]; then
            success "✅ Bitnami image detected: $image"

            # Verify rootless execution
            if [ "$pod_ready" = "True" ]; then
                local uid=$(verify_rootless "$app")
                if [ "$uid" = "1001" ]; then
                    success "✅ Rootless execution verified: UID $uid"
                    APP_STATUS[$app]="success"
                    APP_FAILURES[$app]=0
                    return 0
                elif [ "$uid" != "NotFound" ] && [ "$uid" != "failed" ]; then
                    warning "⚠️  Running as UID $uid (expected 1001)"
                fi
            fi
        fi

        # Failure detection
        if [ "$phase" = "CrashLoopBackOff" ] || [ "$phase" = "Error" ] || [ "$restarts" -gt 5 ]; then
            APP_FAILURES[$app]=$((APP_FAILURES[$app] + 1))
            error "Failure detected: Phase=$phase, Restarts=$restarts (Failure count: ${APP_FAILURES[$app]}/$ROLLBACK_THRESHOLD)"

            if [ ${APP_FAILURES[$app]} -ge $ROLLBACK_THRESHOLD ]; then
                error "ROLLBACK THRESHOLD REACHED FOR $app"
                APP_ROLLBACK_NEEDED[$app]=1
                perform_rollback "$app"
                APP_STATUS[$app]="rolled_back"
                return 1
            fi

            # Show recent logs for debugging
            log "Recent pod logs:"
            kubectl logs "${app}-0" -n "$NAMESPACE" --tail=10 2>/dev/null || true
        else
            # Reset failure count on success
            if [ "$pod_ready" = "True" ] && [ "$phase" = "Running" ]; then
                APP_FAILURES[$app]=0
            fi
        fi

        sleep $CHECK_INTERVAL
        elapsed=$((elapsed + CHECK_INTERVAL))
    done

    # Timeout reached
    warning "Monitoring timeout reached for $app"
    APP_STATUS[$app]="timeout"
    return 1
}

# Main monitoring loop
main() {
    header "Rootless Deployment Monitor - Starting"

    log "Monitoring applications: ${APPS[*]}"
    log "Namespace: $NAMESPACE"
    log "Backup directory: $BACKUP_DIR"
    log "Log file: $LOG_FILE"
    echo ""

    # Backup current state for all apps
    for app in "${APPS[@]}"; do
        backup_current_state "$app"
    done

    header "Monitoring Deployment Progress"

    # Monitor each app in sequence
    for app in "${APPS[@]}"; do
        log "Starting monitoring for $app..."
        monitor_app "$app" &
    done

    # Wait for all monitoring to complete
    wait

    # Final report
    header "Deployment Summary"

    local total=${#APPS[@]}
    local successful=0
    local failed=0
    local rolled_back=0

    for app in "${APPS[@]}"; do
        local status=${APP_STATUS[$app]:-"unknown"}

        case $status in
            success)
                success "$app: Successfully deployed and verified"
                successful=$((successful + 1))
                ;;
            rolled_back)
                error "$app: Failed and rolled back to previous version"
                rolled_back=$((rolled_back + 1))
                ;;
            timeout)
                warning "$app: Monitoring timeout, manual verification needed"
                failed=$((failed + 1))
                ;;
            *)
                warning "$app: Unknown status ($status)"
                failed=$((failed + 1))
                ;;
        esac
    done

    echo ""
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "Total Apps: $total"
    log "Successful: $successful"
    log "Failed: $failed"
    log "Rolled Back: $rolled_back"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Overall status
    if [ $successful -eq $total ]; then
        success "🎉 ALL DEPLOYMENTS SUCCESSFUL"
        log "Cluster security improved: Database layer now 100% rootless"
        exit 0
    elif [ $rolled_back -gt 0 ]; then
        error "❌ ROLLBACK PERFORMED - Some deployments failed and were reverted"
        log "Check logs at: $LOG_FILE"
        log "Backups at: $BACKUP_DIR"
        exit 2
    else
        warning "⚠️  PARTIAL SUCCESS - Some deployments need manual verification"
        log "Check logs at: $LOG_FILE"
        exit 1
    fi
}

# Cleanup on exit
cleanup() {
    log "Monitoring stopped"
}
trap cleanup EXIT

# Run main monitoring
main
