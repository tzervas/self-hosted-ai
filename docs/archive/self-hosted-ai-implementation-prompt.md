# Self-Hosted AI Platform Implementation Prompt

> **Role**: You are implementing a self-hosted AI Kubernetes platform on a dual-node k3s homelab cluster. Follow this prompt with the accompanying Context Document for all configuration details, mappings, and success criteria.

---

## Environment

- **homelab** (192.168.1.170): Primary server, 28 cores/56 threads, ~120GB RAM
- **akula-prime** (192.168.1.99): GPU worker, RTX 5080 16GB VRAM
- **Network**: LAN-only, no internet exposure
- **GitOps**: ArgoCD + Helmfile, GitLab-primary with GitHub mirroring

---

## Implementation Phases

### Phase 1: Storage Foundation
1. Create btrfs subvolume at `/var/lib/longhorn` with `compress=zstd:1,noatime,space_cache=v2`
2. Install Longhorn with two StorageClasses:
   - `longhorn-homelab`: 2 replicas, best-effort locality (default)
   - `longhorn-gpu-local`: 1 replica, strict-local for GPU node
3. Configure recurring snapshots (daily, 7-day retention)

**Validation**: `kubectl get sc` shows both classes; `btrfs fi usage` confirms mount

### Phase 2: GitOps Bootstrap
1. Install ArgoCD in `argocd` namespace
2. Install SealedSecrets, backup sealing keys immediately
3. Create app-of-apps root Application with sync waves (-2 to +3)
4. Configure multi-source Applications for public charts + private values

**Validation**: `argocd app list` shows root app healthy; secrets sealed and committed

### Phase 3: Security Policies
1. Install Kyverno (single replica)
2. Apply baseline policies: require-non-root, disallow-privileged, disallow-latest-tag
3. Create PolicyExceptions for system namespaces (kube-system, kyverno, gpu-workloads)
4. Apply NetworkPolicies: default-deny per namespace, explicit allow for LAN access

**Validation**: `kubectl get clusterpolicy`; test policy blocks non-compliant pod

### Phase 4: Core Services
1. Deploy GitLab CE with resource-optimized values (<8GB RAM baseline)
2. Deploy Ollama on GPU node with `longhorn-gpu-local` storage
3. Deploy LiteLLM, Open WebUI, n8n, SearXNG on homelab node
4. Configure Traefik IngressRoutes with self-signed certs

**Validation**: All ArgoCD apps synced and healthy; services accessible via Traefik

### Phase 5: CI/CD Runners
1. Install ARC controller in `arc-systems` namespace
2. Create GitHub App for authentication (not PAT)
3. Deploy org-level runner scale set with repository restrictions
4. Deploy GitLab Runner in Kubernetes executor mode

**Validation**: `gh api /orgs/ORG/actions/runners` shows registered runner; test workflow passes

### Phase 6: Testing & Quality Gates
1. Configure pre-commit hooks (see Context Document for `.pre-commit-config.yaml`)
2. Setup CI pipeline stages: lint → validate → security → policy
3. Integrate Trivy Operator for runtime scanning
4. Generate policy reports and verify accessibility

**Validation**: `pre-commit run --all-files` passes; CI pipeline green on test commit

---

## Guardrails (Enforce at Every Step)

| Layer | Tool | Action |
|-------|------|--------|
| **Pre-commit** | ruff, shellcheck, yamllint, kubeconform, detect-secrets | Block commits failing checks |
| **CI Pipeline** | helm lint, kubeconform, trivy config, kyverno apply | Fail PR on violations |
| **Admission** | Kyverno | Enforce baseline policies, audit restricted |
| **Runtime** | Trivy Operator | Scan existing workloads, report vulnerabilities |
| **GitOps** | ArgoCD | selfHeal + prune enabled, require healthy sync |

---

## Quality Standards

- **Python**: PEP8 via Ruff, Black formatting, type hints with mypy
- **Bash**: shellcheck (severity=warning), shfmt formatting
- **YAML**: yamllint with Kubernetes-aware config
- **Helm**: helm-docs for READMEs, ct lint for chart testing
- **Commits**: Conventional commits, signed if keys configured

---

## Workflow: Local → CI → Cluster

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Local     │───▶│   CI/CD     │───▶│  Admission  │───▶│   Runtime   │
│             │    │             │    │             │    │             │
│ pre-commit  │    │ lint        │    │ Kyverno     │    │ Trivy Op    │
│ ruff        │    │ kubeconform │    │ NetworkPol  │    │ Pod Sec Std │
│ shellcheck  │    │ trivy       │    │ PSS Labels  │    │ Monitoring  │
│ kubeconform │    │ kyverno     │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     BLOCK              FAIL              REJECT             ALERT
```

---

## Critical Constraints

1. **No plaintext secrets in git** — Use SealedSecrets exclusively
2. **No `:latest` tags** — Pin all image versions
3. **No privileged containers** — Except gpu-workloads namespace
4. **No hardcoded values in Helm** — Parameterize via values.yaml
5. **No manual kubectl applies** — All changes via GitOps

---

## Success Criteria Reference

Refer to Context Document for complete checklist. Key milestones:

- [ ] Storage: Longhorn healthy, both StorageClasses available
- [ ] GitOps: ArgoCD app-of-apps deployed, all apps synced
- [ ] Security: Kyverno enforcing, NetworkPolicies applied
- [ ] Services: GitLab, Ollama, LiteLLM, Open WebUI accessible
- [ ] CI/CD: ARC runners registered, GitLab Runner operational
- [ ] Quality: Pre-commit passing, CI pipeline green

---

## Commands Quick Reference

```bash
# Validate manifests locally
helm template ./charts/app | kubeconform -strict -summary
kyverno apply policies/ --resource manifests/ --table

# Check cluster state
argocd app list
kubectl get policyreport -A
kubectl -n longhorn-system get volumes.longhorn.io

# Seal a secret
kubectl create secret generic mysecret --from-literal=key=value \
  --dry-run=client -o yaml | kubeseal -o yaml > sealed-mysecret.yaml

# Test runner
gh workflow run test.yml --repo ORG/REPO
```

---

**Start with Phase 1. Validate each phase before proceeding. Reference Context Document for all configuration specifics.**
