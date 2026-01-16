#!/usr/bin/env bash
# =============================================================================
# Self-Hosted AI Stack - Cluster Health Verification Script
# =============================================================================
# This script performs comprehensive health checks on the cluster:
# 1. ArgoCD application sync status
# 2. Pod health across all namespaces
# 3. PVC binding status
# 4. Ingress endpoint availability
# 5. Service connectivity
# 6. Certificate status
#
# Usage:
#   ./scripts/verify-cluster-health.sh [--quick] [--verbose] [--wait]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
QUICK_CHECK=false
VERBOSE=false
WAIT_FOR_HEALTHY=false
MAX_WAIT_TIME=600  # 10 minutes
DOMAIN="vectorweight.com"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[⚠]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*" >&2; }
log_step() { echo -e "${CYAN}[STEP]${NC} $*"; }
log_check() { echo -e "${MAGENTA}[CHECK]${NC} $*"; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_CHECK=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --wait)
            WAIT_FOR_HEALTHY=true
            shift
            ;;
        --max-wait)
            MAX_WAIT_TIME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--quick] [--verbose] [--wait] [--max-wait <seconds>]"
            echo ""
            echo "Options:"
            echo "  --quick      Run quick checks only (skip endpoint tests)"
            echo "  --verbose    Show detailed output"
            echo "  --wait       Wait for cluster to become healthy"
            echo "  --max-wait   Maximum wait time in seconds (default: 600)"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Health Check Functions
# =============================================================================

# Track overall health
HEALTH_SCORE=0
TOTAL_CHECKS=0
FAILED_CHECKS=0

record_check() {
    local name="$1"
    local status="$2"  # pass/fail/warn
    
    ((TOTAL_CHECKS++))
    
    case "$status" in
        pass)
            log_success "$name"
            ((HEALTH_SCORE++))
            ;;
        warn)
            log_warn "$name"
            ;;
        fail)
            log_error "$name"
            ((FAILED_CHECKS++))
            ;;
    esac
}

# Check cluster connectivity
check_cluster_connectivity() {
    log_step "Checking cluster connectivity..."
    
    if kubectl cluster-info &> /dev/null; then
        record_check "Kubernetes API server reachable" "pass"
    else
        record_check "Kubernetes API server reachable" "fail"
        return 1
    fi
    
    # Check nodes
    local ready_nodes
    ready_nodes=$(kubectl get nodes --no-headers | grep -c " Ready" || echo "0")
    local total_nodes
    total_nodes=$(kubectl get nodes --no-headers | wc -l)
    
    if [[ "$ready_nodes" -eq "$total_nodes" && "$total_nodes" -gt 0 ]]; then
        record_check "All nodes ready ($ready_nodes/$total_nodes)" "pass"
    else
        record_check "Nodes ready ($ready_nodes/$total_nodes)" "warn"
    fi
}

# Check ArgoCD applications
check_argocd_apps() {
    log_step "Checking ArgoCD applications..."
    
    if ! kubectl get namespace argocd &> /dev/null; then
        record_check "ArgoCD namespace exists" "fail"
        return 1
    fi
    
    record_check "ArgoCD namespace exists" "pass"
    
    # Get application status
    local apps
    apps=$(kubectl get applications -n argocd -o json 2>/dev/null)
    
    if [[ -z "$apps" || "$apps" == "null" ]]; then
        record_check "ArgoCD applications found" "warn"
        return 0
    fi
    
    local total_apps
    total_apps=$(echo "$apps" | jq '.items | length')
    
    local synced_apps
    synced_apps=$(echo "$apps" | jq '[.items[] | select(.status.sync.status == "Synced")] | length')
    
    local healthy_apps
    healthy_apps=$(echo "$apps" | jq '[.items[] | select(.status.health.status == "Healthy")] | length')
    
    if [[ "$synced_apps" -eq "$total_apps" ]]; then
        record_check "All applications synced ($synced_apps/$total_apps)" "pass"
    else
        record_check "Applications synced ($synced_apps/$total_apps)" "warn"
        
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "Out-of-sync applications:"
            echo "$apps" | jq -r '.items[] | select(.status.sync.status != "Synced") | "  - " + .metadata.name + " (" + .status.sync.status + ")"'
        fi
    fi
    
    if [[ "$healthy_apps" -eq "$total_apps" ]]; then
        record_check "All applications healthy ($healthy_apps/$total_apps)" "pass"
    else
        record_check "Applications healthy ($healthy_apps/$total_apps)" "warn"
        
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "Unhealthy applications:"
            echo "$apps" | jq -r '.items[] | select(.status.health.status != "Healthy") | "  - " + .metadata.name + " (" + .status.health.status + ")"'
        fi
    fi
}

# Check pod health
check_pod_health() {
    log_step "Checking pod health..."
    
    local namespaces=("ai-services" "gpu-workloads" "automation" "monitoring" "traefik" "argocd" "cert-manager" "longhorn-system")
    
    for ns in "${namespaces[@]}"; do
        if ! kubectl get namespace "$ns" &> /dev/null; then
            [[ "$VERBOSE" == "true" ]] && log_info "Namespace $ns does not exist yet"
            continue
        fi
        
        local pods
        pods=$(kubectl get pods -n "$ns" --no-headers 2>/dev/null || true)
        
        if [[ -z "$pods" ]]; then
            continue
        fi
        
        local total
        total=$(echo "$pods" | wc -l)
        
        local running
        running=$(echo "$pods" | grep -c "Running\|Completed" || echo "0")
        
        if [[ "$running" -eq "$total" ]]; then
            record_check "Pods in $ns ($running/$total running)" "pass"
        else
            record_check "Pods in $ns ($running/$total running)" "warn"
            
            if [[ "$VERBOSE" == "true" ]]; then
                log_info "Non-running pods in $ns:"
                echo "$pods" | grep -v "Running\|Completed" | awk '{print "  - " $1 " (" $3 ")"}'
            fi
        fi
    done
}

# Check PVC status
check_pvc_status() {
    log_step "Checking PVC status..."
    
    local pvcs
    pvcs=$(kubectl get pvc -A --no-headers 2>/dev/null || true)
    
    if [[ -z "$pvcs" ]]; then
        record_check "No PVCs found" "pass"
        return 0
    fi
    
    local total
    total=$(echo "$pvcs" | wc -l)
    
    local bound
    bound=$(echo "$pvcs" | grep -c "Bound" || echo "0")
    
    if [[ "$bound" -eq "$total" ]]; then
        record_check "All PVCs bound ($bound/$total)" "pass"
    else
        record_check "PVCs bound ($bound/$total)" "warn"
        
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "Unbound PVCs:"
            echo "$pvcs" | grep -v "Bound" | awk '{print "  - " $1 "/" $2 " (" $4 ")"}'
        fi
    fi
}

# Check certificates
check_certificates() {
    log_step "Checking TLS certificates..."
    
    if ! kubectl get crd certificates.cert-manager.io &> /dev/null; then
        record_check "cert-manager CRDs installed" "warn"
        return 0
    fi
    
    record_check "cert-manager CRDs installed" "pass"
    
    local certs
    certs=$(kubectl get certificates -A -o json 2>/dev/null || echo '{"items":[]}')
    
    local total
    total=$(echo "$certs" | jq '.items | length')
    
    if [[ "$total" -eq 0 ]]; then
        record_check "No certificates created yet" "warn"
        return 0
    fi
    
    local ready
    ready=$(echo "$certs" | jq '[.items[] | select(.status.conditions[]?.type == "Ready" and .status.conditions[]?.status == "True")] | length')
    
    if [[ "$ready" -eq "$total" ]]; then
        record_check "All certificates ready ($ready/$total)" "pass"
    else
        record_check "Certificates ready ($ready/$total)" "warn"
        
        if [[ "$VERBOSE" == "true" ]]; then
            log_info "Pending certificates:"
            echo "$certs" | jq -r '.items[] | select(.status.conditions[]?.status != "True") | "  - " + .metadata.namespace + "/" + .metadata.name'
        fi
    fi
}

# Check ingress endpoints
check_ingress_endpoints() {
    if [[ "$QUICK_CHECK" == "true" ]]; then
        log_info "Skipping endpoint checks (--quick mode)"
        return 0
    fi
    
    log_step "Checking ingress endpoints..."
    
    local endpoints=(
        "ai.${DOMAIN}"
        "llm.${DOMAIN}"
        "argocd.${DOMAIN}"
        "traefik.${DOMAIN}"
    )
    
    for endpoint in "${endpoints[@]}"; do
        # Try HTTPS first
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -k "https://${endpoint}" 2>/dev/null || echo "000")
        
        if [[ "$http_code" == "200" || "$http_code" == "301" || "$http_code" == "302" || "$http_code" == "401" || "$http_code" == "403" ]]; then
            record_check "Endpoint https://${endpoint} (HTTP $http_code)" "pass"
        elif [[ "$http_code" == "000" ]]; then
            record_check "Endpoint https://${endpoint} (unreachable)" "warn"
        else
            record_check "Endpoint https://${endpoint} (HTTP $http_code)" "warn"
        fi
    done
}

# Check service connectivity
check_service_connectivity() {
    if [[ "$QUICK_CHECK" == "true" ]]; then
        return 0
    fi
    
    log_step "Checking internal service connectivity..."
    
    # Check if we can resolve services
    local services=(
        "ollama.ai-services:11434"
        "litellm.ai-services:4000"
        "redis-master.ai-services:6379"
        "postgresql.ai-services:5432"
    )
    
    for svc in "${services[@]}"; do
        local name="${svc%%:*}"
        local port="${svc##*:}"
        
        # Use kubectl to check if service exists
        local ns="${name##*.}"
        local svc_name="${name%%.*}"
        
        if kubectl get svc "$svc_name" -n "$ns" &> /dev/null; then
            record_check "Service $name:$port exists" "pass"
        else
            record_check "Service $name:$port exists" "warn"
        fi
    done
}

# Check GPU availability
check_gpu_availability() {
    log_step "Checking GPU availability..."
    
    # Check if GPU operator is installed
    if ! kubectl get namespace gpu-operator &> /dev/null; then
        record_check "GPU operator namespace exists" "warn"
        return 0
    fi
    
    record_check "GPU operator namespace exists" "pass"
    
    # Check for GPU nodes
    local gpu_nodes
    gpu_nodes=$(kubectl get nodes -o json | jq '[.items[] | select(.status.allocatable["nvidia.com/gpu"] != null)] | length')
    
    if [[ "$gpu_nodes" -gt 0 ]]; then
        record_check "GPU nodes available ($gpu_nodes)" "pass"
    else
        record_check "GPU nodes available" "warn"
    fi
}

# =============================================================================
# Wait for Healthy
# =============================================================================

wait_for_healthy() {
    log_step "Waiting for cluster to become healthy (max ${MAX_WAIT_TIME}s)..."
    
    local start_time
    start_time=$(date +%s)
    local elapsed=0
    
    while [[ $elapsed -lt $MAX_WAIT_TIME ]]; do
        # Reset counters
        HEALTH_SCORE=0
        TOTAL_CHECKS=0
        FAILED_CHECKS=0
        
        # Run checks silently
        exec 3>&1 4>&2
        exec 1>/dev/null 2>&1
        
        check_cluster_connectivity || true
        check_argocd_apps || true
        check_pod_health || true
        check_pvc_status || true
        
        exec 1>&3 2>&4
        
        local health_pct=$((HEALTH_SCORE * 100 / TOTAL_CHECKS))
        
        if [[ $FAILED_CHECKS -eq 0 && $health_pct -ge 90 ]]; then
            log_success "Cluster is healthy! (${health_pct}% health score)"
            return 0
        fi
        
        elapsed=$(($(date +%s) - start_time))
        log_info "Waiting... (${elapsed}s elapsed, ${health_pct}% healthy)"
        sleep 10
    done
    
    log_error "Timeout waiting for cluster to become healthy"
    return 1
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│                   SELF-HOSTED AI - CLUSTER HEALTH CHECK                      │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"
    echo ""
    
    if [[ "$WAIT_FOR_HEALTHY" == "true" ]]; then
        wait_for_healthy
        echo ""
    fi
    
    # Run all checks
    check_cluster_connectivity || true
    echo ""
    
    check_argocd_apps || true
    echo ""
    
    check_pod_health || true
    echo ""
    
    check_pvc_status || true
    echo ""
    
    check_certificates || true
    echo ""
    
    check_gpu_availability || true
    echo ""
    
    check_ingress_endpoints || true
    echo ""
    
    check_service_connectivity || true
    echo ""
    
    # Final summary
    local health_pct=0
    if [[ $TOTAL_CHECKS -gt 0 ]]; then
        health_pct=$((HEALTH_SCORE * 100 / TOTAL_CHECKS))
    fi
    
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│                           HEALTH CHECK SUMMARY                               │"
    echo "├─────────────────────────────────────────────────────────────────────────────┤"
    printf "│  Total Checks:    %-58d│\n" "$TOTAL_CHECKS"
    printf "│  Passed:          %-58d│\n" "$HEALTH_SCORE"
    printf "│  Failed:          %-58d│\n" "$FAILED_CHECKS"
    printf "│  Health Score:    %-58s│\n" "${health_pct}%"
    echo "├─────────────────────────────────────────────────────────────────────────────┤"
    
    if [[ $health_pct -ge 90 ]]; then
        echo "│  Status:          ✅ HEALTHY                                                │"
    elif [[ $health_pct -ge 70 ]]; then
        echo "│  Status:          ⚠️  DEGRADED                                               │"
    else
        echo "│  Status:          ❌ UNHEALTHY                                               │"
    fi
    
    echo "└─────────────────────────────────────────────────────────────────────────────┘"
    echo ""
    
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
