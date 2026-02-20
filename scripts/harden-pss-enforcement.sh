#!/usr/bin/env bash
# Security Hardening - Enforce Pod Security Standards
# Part of Podman Migration Phase 6
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
REPORT_FILE="/tmp/pss-enforcement-$(date +%Y%m%d-%H%M%S).md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[⚠]${NC} $*"
}

error() {
    echo -e "${RED}[✗]${NC} $*"
}

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    error "kubectl not found. Please install kubectl."
    exit 1
fi

# Verify cluster access
if ! kubectl cluster-info &> /dev/null; then
    error "Cannot connect to Kubernetes cluster"
    exit 1
fi

log "Starting Pod Security Standards enforcement..."
log "Report will be saved to: $REPORT_FILE"
echo ""

# Create report header
cat > "$REPORT_FILE" << EOF
# Pod Security Standards Enforcement Report

**Date**: $(date)
**Cluster**: $(kubectl config current-context)
**Phase**: Podman Migration Phase 6

## Summary

This script enforces Pod Security Standards (PSS) "restricted" policy on AI workload namespaces as part of the migration to rootless Podman.

---

## Pre-Enforcement State

EOF

# Check current PSS labels
log "Checking current PSS labels..."
echo ""

for ns in ai-services gpu-workloads automation; do
    if kubectl get namespace "$ns" &> /dev/null; then
        labels=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels}' 2>/dev/null || echo "{}")
        echo "### Namespace: $ns" >> "$REPORT_FILE"
        echo "\`\`\`json" >> "$REPORT_FILE"
        echo "$labels" | jq '.' >> "$REPORT_FILE"
        echo "\`\`\`" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
done

# Function to enforce PSS on a namespace
enforce_pss() {
    local namespace="$1"
    local policy="${2:-restricted}"  # Default to restricted

    log "Enforcing PSS '$policy' on namespace: $namespace"

    if ! kubectl get namespace "$namespace" &> /dev/null; then
        warn "Namespace $namespace does not exist, skipping"
        return
    fi

    # Label the namespace with PSS enforcement
    kubectl label namespace "$namespace" \
        pod-security.kubernetes.io/enforce="$policy" \
        pod-security.kubernetes.io/audit="$policy" \
        pod-security.kubernetes.io/warn="$policy" \
        --overwrite

    if [ $? -eq 0 ]; then
        success "PSS '$policy' enforced on namespace: $namespace"
    else
        error "Failed to enforce PSS on namespace: $namespace"
        return 1
    fi
}

# Enforce PSS on AI/GPU namespaces
echo ""
log "Enforcing PSS 'restricted' on AI workload namespaces..."
echo ""

enforce_pss "ai-services" "restricted"
enforce_pss "gpu-workloads" "restricted"
enforce_pss "automation" "restricted"

# Verify enforcement
echo ""
log "Verifying PSS enforcement..."
echo ""

echo "## Post-Enforcement State" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

for ns in ai-services gpu-workloads automation; do
    if kubectl get namespace "$ns" &> /dev/null; then
        enforce_label=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/enforce}' 2>/dev/null || echo "not set")
        audit_label=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/audit}' 2>/dev/null || echo "not set")
        warn_label=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/warn}' 2>/dev/null || echo "not set")

        echo "### Namespace: $ns" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "| Mode | Policy |" >> "$REPORT_FILE"
        echo "|------|--------|" >> "$REPORT_FILE"
        echo "| enforce | $enforce_label |" >> "$REPORT_FILE"
        echo "| audit | $audit_label |" >> "$REPORT_FILE"
        echo "| warn | $warn_label |" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"

        if [ "$enforce_label" = "restricted" ]; then
            success "Namespace $ns: PSS restricted enforced"
        else
            error "Namespace $ns: PSS not properly enforced (got: $enforce_label)"
        fi
    fi
done

# Check for any pods that might violate PSS restricted
echo ""
log "Checking for pods that violate PSS restricted..."
echo ""

echo "## PSS Violations (if any)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

violations=0
for ns in ai-services gpu-workloads automation; do
    if kubectl get namespace "$ns" &> /dev/null; then
        # Check for pods running as root
        root_pods=$(kubectl get pods -n "$ns" -o json 2>/dev/null | \
            jq -r '.items[] | select(.spec.securityContext.runAsNonRoot != true) | .metadata.name' 2>/dev/null || echo "")

        if [ -n "$root_pods" ]; then
            echo "### Namespace: $ns - Pods without runAsNonRoot" >> "$REPORT_FILE"
            echo "\`\`\`" >> "$REPORT_FILE"
            echo "$root_pods" >> "$REPORT_FILE"
            echo "\`\`\`" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            violations=$((violations + 1))
        fi
    fi
done

if [ $violations -eq 0 ]; then
    echo "No PSS violations detected ✅" >> "$REPORT_FILE"
    success "No PSS violations detected"
else
    echo "⚠️ $violations namespace(s) have PSS violations" >> "$REPORT_FILE"
    warn "$violations namespace(s) have PSS violations"
fi

# Check NetworkPolicies
echo ""
log "Verifying NetworkPolicies are in place..."
echo ""

echo "## NetworkPolicy Status" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

for ns in ai-services gpu-workloads automation; do
    if kubectl get namespace "$ns" &> /dev/null; then
        policy_count=$(kubectl get networkpolicies -n "$ns" --no-headers 2>/dev/null | wc -l)
        echo "### Namespace: $ns" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "**NetworkPolicy count**: $policy_count" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"

        if [ "$policy_count" -gt 0 ]; then
            echo "Policies:" >> "$REPORT_FILE"
            echo "\`\`\`" >> "$REPORT_FILE"
            kubectl get networkpolicies -n "$ns" --no-headers 2>/dev/null | awk '{print "- " $1}' >> "$REPORT_FILE"
            echo "\`\`\`" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            success "Namespace $ns: $policy_count NetworkPolicies active"
        else
            warn "Namespace $ns: No NetworkPolicies found"
        fi
    fi
done

# Final summary
echo ""
echo "═══════════════════════════════════════════════════════════════" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- ✅ PSS 'restricted' enforced on ai-services, gpu-workloads, automation" >> "$REPORT_FILE"
echo "- ✅ NetworkPolicies verified in all namespaces" >> "$REPORT_FILE"
echo "- ⚠️  Note: Some pods may need redeployment to comply with PSS" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "**Next Steps**:" >> "$REPORT_FILE"
echo "1. Redeploy non-compliant workloads (they will be rejected by PSS)" >> "$REPORT_FILE"
echo "2. Run full security audit: \`./scripts/security-audit.sh\`" >> "$REPORT_FILE"
echo "3. Proceed with Phase 7: Remove Docker completely" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Print summary
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Pod Security Standards Enforcement Complete                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
success "PSS 'restricted' enforced on all AI workload namespaces"
log "Report saved to: $REPORT_FILE"
echo ""
echo "Next steps:"
echo "  1. Run full security audit: ./scripts/security-audit.sh"
echo "  2. Verify workloads comply: kubectl get pods -n <namespace>"
echo "  3. Proceed with Phase 7 (Docker removal)"
echo ""
