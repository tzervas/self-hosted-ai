#!/usr/bin/env bash
# Security Posture Audit - Rootless Deployment Phase 1
set -euo pipefail

REPORT_FILE="/tmp/security-audit-$(date +%Y%m%d-%H%M%S).md"

echo "# Security Posture Audit Report" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "**Date**: $(date)" >> "$REPORT_FILE"
echo "**Cluster**: $(kubectl config current-context)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log() {
    echo "$*" | tee -a "$REPORT_FILE"
}

log "## 1. Pods Running as Root"
log ""
log "\`\`\`"
kubectl get pods -A -o json | \
  jq -r '.items[] | select(.spec.securityContext.runAsNonRoot != true and .spec.securityContext.runAsUser != 1000 and .spec.securityContext.runAsUser != 1001) | "\(.metadata.namespace)/\(.metadata.name): runAsNonRoot=\(.spec.securityContext.runAsNonRoot // "not set"), runAsUser=\(.spec.securityContext.runAsUser // "not set")"' | \
  tee -a "$REPORT_FILE" | head -20
log "\`\`\`"
log ""

root_pods=$(kubectl get pods -A -o json | \
  jq -r '[.items[] | select(.spec.securityContext.runAsNonRoot != true)] | length')
total_pods=$(kubectl get pods -A --no-headers | wc -l)
log "**Summary**: $root_pods/$total_pods pods without runAsNonRoot=true"
log ""

log "## 2. Privileged Containers"
log ""
log "\`\`\`"
kubectl get pods -A -o json | \
  jq -r '.items[] | select(.spec.containers[]?.securityContext.privileged == true) | "\(.metadata.namespace)/\(.metadata.name): \([.spec.containers[] | select(.securityContext.privileged == true) | .name] | join(", "))"' | \
  tee -a "$REPORT_FILE"
log "\`\`\`"
log ""

priv_pods=$(kubectl get pods -A -o json | \
  jq -r '[.items[] | select(.spec.containers[]?.securityContext.privileged == true)] | length')
log "**Summary**: $priv_pods privileged containers found"
log ""

log "## 3. Added Capabilities"
log ""
log "\`\`\`"
kubectl get pods -A -o json | \
  jq -r '.items[] | select(.spec.containers[]?.securityContext.capabilities.add != null) | "\(.metadata.namespace)/\(.metadata.name): \([.spec.containers[] | select(.securityContext.capabilities.add != null) | "\(.name): \(.securityContext.capabilities.add | join(","))")] | join(" | "))"' | \
  tee -a "$REPORT_FILE" | head -20
log "\`\`\`"
log ""

log "## 4. Kyverno Policy Exemptions"
log ""
log "\`\`\`"
kubectl get clusterpolicy pod-security-baseline -o yaml | \
  grep -A 15 "exclude:" | grep "namespaces:" -A 10 | \
  grep "^[[:space:]]*-" | sort -u | \
  tee -a "$REPORT_FILE"
log "\`\`\`"
log ""

exempted_ns=$(kubectl get clusterpolicy pod-security-baseline -o yaml | \
  grep -A 15 "exclude:" | grep "namespaces:" -A 10 | \
  grep "^[[:space:]]*-" | sort -u | wc -l)
log "**Summary**: $exempted_ns namespaces exempted from security policies"
log ""

log "## 5. Security Score"
log ""

non_root_pct=$(( (total_pods - root_pods) * 100 / total_pods ))
log "- **Non-root execution**: $non_root_pct% ($((total_pods - root_pods))/$total_pods pods)"
log "- **Privileged containers**: $priv_pods"
log "- **Policy exemptions**: $exempted_ns namespaces"
log ""

if [ "$non_root_pct" -ge 90 ]; then
    log "**Overall Security Posture**: ✅ EXCELLENT"
elif [ "$non_root_pct" -ge 70 ]; then
    log "**Overall Security Posture**: ✅ GOOD"
elif [ "$non_root_pct" -ge 50 ]; then
    log "**Overall Security Posture**: ⚠️  FAIR"
else
    log "**Overall Security Posture**: ❌ POOR"
fi
log ""

log "## 6. Migration Priority Matrix"
log ""
log "### Quick Wins (Already support non-root)"
log ""
log "Services using Bitnami images (default UID 1001):"
log "\`\`\`"
kubectl get pods -A -o json | \
  jq -r '.items[] | select(.spec.containers[].image | test("bitnami")) | "\(.metadata.namespace)/\(.metadata.name): \(.spec.containers[].image)"' | \
  tee -a "$REPORT_FILE" | head -10
log "\`\`\`"
log ""

log "### Medium Effort (Need PVC permission fixes)"
log ""
log "StatefulSets with PVCs:"
log "\`\`\`"
kubectl get statefulset -A -o json | \
  jq -r '.items[] | "\(.metadata.namespace)/\(.metadata.name): \(.spec.volumeClaimTemplates | length) PVCs"' | \
  tee -a "$REPORT_FILE"
log "\`\`\`"
log ""

log "### Infrastructure (May need to remain privileged)"
log ""
log "Namespaces typically requiring privileges:"
log "- kube-system: Kubernetes system components"
log "- longhorn-system: Storage infrastructure"
log "- linkerd: Service mesh (iptables manipulation)"
log "- cert-manager: Certificate management"
log ""

log "---"
log ""
log "Report saved to: $REPORT_FILE"

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  Security Audit Complete                                           ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Report: $REPORT_FILE"
echo ""
echo "Next steps:"
echo "1. Review the migration priority matrix"
echo "2. Start with 'Quick Wins' (Bitnami images)"
echo "3. Proceed to 'Medium Effort' (StatefulSets with PVCs)"
echo ""
