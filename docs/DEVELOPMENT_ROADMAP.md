# Self-Hosted AI Platform - Development Roadmap

**Last Updated**: 2026-02-06
**Current Branch**: `dev` (merged from main, ready for feature work)
**Status**: Planning Phase → Implementation

---

## Current State Assessment

### ✅ Completed (Merged to dev)

**Infrastructure & GitOps**:
- ✅ Kubernetes (k3s) cluster with 2 nodes (akula-prime + homelab)
- ✅ ArgoCD GitOps with App-of-Apps pattern (sync waves -2 to 7)
- ✅ Helm charts for all services (~20 charts)
- ✅ SealedSecrets for encrypted credentials
- ✅ Traefik ingress with self-signed CA (cert-manager)
- ✅ Longhorn distributed storage
- ✅ Resource quotas and LimitRanges

**SSO & Security**:
- ✅ Keycloak SSO deployment
- ✅ oauth2-proxy for forward authentication
- ✅ OIDC integration for: n8n, SearXNG, LiteLLM, Dify, Grafana, Prometheus, Traefik, Longhorn
- ✅ GitLab OAuth integration
- ✅ Security fixes (python-multipart CVE)

**AI Services**:
- ✅ Ollama (CPU + GPU worker)
- ✅ Open WebUI chat interface
- ✅ LiteLLM API gateway with model routing
- ✅ n8n workflow automation (11 workflows)
- ✅ SearXNG privacy search
- ✅ ComfyUI image generation
- ✅ MCP servers (9 tool servers)

**Multimodal AI**:
- ✅ Audio generation (Bark TTS, AudioLDM2, MusicGen)
- ✅ Video generation (AnimateDiff-Lightning, SVD)
- ✅ Vision analysis (LLaVA workflows)
- ✅ Unified multimodal pipeline (script → video + audio)

**Development Tooling**:
- ✅ Claude Code agents (k8s-validator, python-test-runner, argocd-sync-monitor)
- ✅ Python automation scripts (bootstrap, validate, secrets, models)
- ✅ Pre-commit hooks (conventional commits, linting)
- ✅ Taskfile for common operations
- ✅ Comprehensive documentation (INDEX.md, ARCHITECTURE.md, etc.)

**CI/CD**:
- ✅ GitLab deployment with external PostgreSQL/Redis
- ✅ GitHub Actions Runner Controller (ARC) - planned

### ⚠️ Known Issues (Prioritize)

| Issue | Impact | Priority | Phase |
|-------|--------|----------|-------|
| **GPU operator pods failing** (gpu-feature-discovery, nvidia-device-plugin) | GPU workloads can't schedule | 🔴 High | 1.1 |
| **ComfyUI pending** (no GPU node selector match) | Image generation unavailable | 🔴 High | 1.1 |
| **qemu-binfmt crashes** (init container loop) | ARM64 builds failing | 🟡 Medium | 1.2 |
| **Open WebUI container config error** | Chat UI down | 🔴 High | 1.1 |
| **LiteLLM missing secret** (ai-services namespace) | Duplicate LiteLLM pod issues | 🟡 Medium | 1.2 |
| **ArgoCD CLI unavailable locally** | Manual sync required | 🟢 Low | 1.3 |

### 🎯 Strategic Goals

1. **Stabilize Core Platform** - Fix critical issues, ensure all services healthy
2. **Complete SSO Integration** - Extend oauth2-proxy to all services
3. **Enable GPU Workloads** - Fix GPU operator, schedule ComfyUI/video/audio servers
4. **Enhance Observability** - Grafana dashboards, alerting, log aggregation
5. **Automate Operations** - Pre-commit hooks, CI/CD pipelines, backup/restore
6. **Expand AI Capabilities** - More models, RAG integration, fine-tuning
7. **Improve Developer Experience** - Better documentation, faster iteration

---

## Phase 1: Stabilization & Critical Fixes (Week 1-2)

**Goal**: Achieve 100% service availability, resolve all critical issues

### Phase 1.1: GPU Workload Enablement (Priority 1)

**Objective**: Fix GPU operator and enable ComfyUI/audio/video services

**Tasks**:
- [ ] Investigate GPU operator pod failures (gpu-feature-discovery, nvidia-device-plugin)
  - Check node labels and taints on akula-prime
  - Verify NVIDIA driver installation
  - Review GPU operator logs
- [ ] Fix ComfyUI deployment
  - Add correct GPU node selector
  - Fix resource requests/limits
  - Test image generation workflow
- [ ] Verify Ollama GPU pod scheduling
- [ ] Test audio-server and video-server deployments
- [ ] Document GPU node setup in OPERATIONS.md

**Success Criteria**:
- ✅ All GPU operator pods running without errors
- ✅ ComfyUI pod scheduled and running on akula-prime
- ✅ GPU inference working via Ollama
- ✅ Audio and video generation services operational

**Estimated Time**: 3-4 days

**Branch**: `fix/gpu-workload-enablement` → PR to `dev`

---

### Phase 1.2: Core Service Health (Priority 2)

**Objective**: Resolve all pod failures and container errors

**Tasks**:
- [ ] Fix Open WebUI container config error
  - Check ConfigMap/Secret references
  - Verify volume mounts
  - Test UI accessibility
- [ ] Remove qemu-binfmt or fix init crash
  - Determine if still needed (ARM64 builds via ARC instead?)
  - Remove ArgoCD app if obsolete
  - Or fix init container crash loop
- [ ] Resolve LiteLLM duplicate deployment
  - Keep single LiteLLM instance (consolidate namespaces)
  - Remove duplicate from ai-services or default
  - Ensure litellm-secret exists
- [ ] Health check all services
  - Run `scripts/validate_cluster.py`
  - Generate updated VERIFICATION_REPORT.md

**Success Criteria**:
- ✅ Zero non-running pods (except Completed jobs)
- ✅ Open WebUI accessible at https://ai.vectorweight.com
- ✅ LiteLLM healthy with single deployment
- ✅ All critical services passing health checks

**Estimated Time**: 2-3 days

**Branch**: `fix/core-service-health` → PR to `dev`

---

### Phase 1.3: Observability Enhancements (Priority 3)

**Objective**: Improve monitoring, logging, and debugging capabilities

**Tasks**:
- [ ] Deploy Loki for log aggregation
  - Add Helm chart in `helm/loki/`
  - Configure Promtail DaemonSet
  - Integrate with Grafana
- [ ] Create Grafana dashboards
  - Cluster health (nodes, pods, resources)
  - AI services (Ollama, LiteLLM, Open WebUI)
  - ArgoCD sync status
- [ ] Set up Alertmanager
  - Alert on pod failures
  - Alert on service unavailability
  - Alert on resource exhaustion
- [ ] Install ArgoCD CLI locally
  - Add to PATH
  - Configure authentication
  - Test `argocd app sync`

**Success Criteria**:
- ✅ Loki ingesting logs from all namespaces
- ✅ 5+ Grafana dashboards for different perspectives
- ✅ Alertmanager sending notifications (Slack/email)
- ✅ ArgoCD CLI functional for local ops

**Estimated Time**: 3-4 days

**Branch**: `feat/observability-stack` → PR to `dev`

---

## Phase 2: SSO Completion & Security Hardening (Week 3-4)

**Goal**: Unified SSO for all services, enhanced security posture

### Phase 2.1: Complete SSO Integration

**Tasks**:
- [ ] Extend oauth2-proxy to remaining services
  - GitLab (currently has OAuth, add forward-auth)
  - ArgoCD (currently exposed, add SSO)
  - Grafana (OIDC integration)
  - Keycloak admin console (self-protecting)
- [ ] Test SSO flows end-to-end
  - Single login across all services
  - Session persistence
  - Logout propagation
- [ ] Document SSO architecture
  - Update ARCHITECTURE.md with SSO ADR
  - Add SSO troubleshooting to OPERATIONS.md

**Success Criteria**:
- ✅ All external services behind Keycloak SSO
- ✅ Single login works across platform
- ✅ SSO documentation complete

**Estimated Time**: 4-5 days

**Branch**: `feat/complete-sso` → PR to `dev`

---

### Phase 2.2: Security Hardening

**Tasks**:
- [ ] Enable Kyverno policies
  - Policy enforcement for all namespaces
  - Require non-root containers
  - Require resource limits
  - Block latest tags
- [ ] Implement network policies
  - Namespace isolation
  - Allow only required ingress/egress
  - Block cross-namespace traffic except allowed
- [ ] Rotate all secrets
  - Use `scripts/secrets_manager.py rotate`
  - Update SealedSecrets
  - Sync via ArgoCD
- [ ] Security audit
  - Run Trivy scans on all images
  - Check for CVEs in dependencies
  - Review RBAC permissions

**Success Criteria**:
- ✅ Kyverno policies active and enforcing
- ✅ Network policies in all namespaces
- ✅ All secrets rotated within last 30 days
- ✅ Zero critical CVEs in production images

**Estimated Time**: 5-6 days

**Branch**: `feat/security-hardening` → PR to `dev`

---

## Phase 3: AI Capabilities Expansion (Week 5-6)

**Goal**: Add more models, enable RAG, improve AI workflows

### Phase 3.1: RAG Integration

**Tasks**:
- [ ] Deploy vector database (Chroma or Qdrant)
  - Add Helm chart
  - Configure persistence
  - Expose API via ingress
- [ ] Integrate with Open WebUI
  - Enable document upload
  - Configure embedding model
  - Test retrieval-augmented generation
- [ ] Create RAG workflows in n8n
  - Document ingestion pipeline
  - Query-time retrieval workflow
  - Update existing agentic workflows
- [ ] Index project documentation
  - Use `scripts/rag_index.py`
  - Generate embeddings for all docs
  - Create searchable knowledge base

**Success Criteria**:
- ✅ Vector DB running and persistent
- ✅ Open WebUI RAG functional with document upload
- ✅ n8n workflows using RAG for context
- ✅ Project docs indexed and searchable

**Estimated Time**: 4-5 days

**Branch**: `feat/rag-integration` → PR to `dev`

---

### Phase 3.2: Model Expansion

**Tasks**:
- [ ] Add more Ollama models
  - Larger code models (deepseek-coder:33b, codellama:70b)
  - Multimodal models (llava:34b, bakllava:13b)
  - Specialized models (sqlcoder, meditron)
- [ ] Configure LiteLLM routing
  - Add model fallbacks
  - Enable load balancing
  - Set rate limits per model
- [ ] Optimize GPU memory usage
  - Test model quantization (4-bit, 8-bit)
  - Configure model offloading
  - Monitor VRAM usage
- [ ] Update model manifest
  - Document model purposes
  - Add recommended use cases
  - Update config/models-manifest.yml

**Success Criteria**:
- ✅ 10+ new models available
- ✅ LiteLLM routing optimized
- ✅ GPU memory usage stable
- ✅ Model documentation complete

**Estimated Time**: 3-4 days

**Branch**: `feat/model-expansion` → PR to `dev`

---

### Phase 3.3: Workflow Automation Enhancements

**Tasks**:
- [ ] Create agent orchestration workflows
  - Multi-agent debate/consensus
  - Hierarchical task delegation
  - Feedback loop workflows
- [ ] Add external integrations
  - GitHub API (issue creation, PR comments)
  - Slack notifications
  - Email alerts
- [ ] Enhance ComfyUI workflows
  - Image upscaling pipelines
  - Style transfer workflows
  - Batch processing support
- [ ] Document all workflows
  - Purpose and use cases
  - API endpoints and parameters
  - Example requests/responses

**Success Criteria**:
- ✅ 5+ new n8n workflows operational
- ✅ External integrations working (GitHub, Slack)
- ✅ ComfyUI workflows documented
- ✅ All workflows have API examples

**Estimated Time**: 4-5 days

**Branch**: `feat/workflow-enhancements` → PR to `dev`

---

## Phase 4: Operations Automation (Week 7-8)

**Goal**: Automate routine operations, improve reliability

### Phase 4.1: Backup & Disaster Recovery

**Tasks**:
- [ ] Deploy Velero for cluster backups
  - Configure S3/MinIO backend
  - Schedule automated backups
  - Test restore procedures
- [ ] Implement Longhorn snapshots
  - Automated PV snapshots
  - Retention policies
  - Cross-node replication
- [ ] Create backup scripts
  - PostgreSQL database backups
  - Redis RDB snapshots
  - Keycloak realm exports
- [ ] Document disaster recovery
  - Recovery time objectives (RTO)
  - Recovery point objectives (RPO)
  - Step-by-step restore procedures

**Success Criteria**:
- ✅ Velero backing up cluster daily
- ✅ Longhorn snapshots automated
- ✅ Database backups verified restorable
- ✅ DR documentation complete

**Estimated Time**: 4-5 days

**Branch**: `feat/backup-dr` → PR to `dev`

---

### Phase 4.2: CI/CD Pipeline Enhancement

**Tasks**:
- [ ] Deploy GitHub Actions Runner Controller (ARC)
  - Configure runner sets (amd64, gpu, arm64)
  - Set up autoscaling (scale-to-zero)
  - Test runner pods
- [ ] Create CI workflows
  - Helm chart validation on PR
  - Docker image builds (audio-server, video-server)
  - Pytest for Python agents
- [ ] Set up CD workflows
  - Auto-sync ArgoCD on main branch push
  - Rollback on failed health checks
  - Slack notifications for deployments
- [ ] Enable pre-merge validation
  - Require passing CI checks
  - Require approval for main branch PRs
  - Enforce conventional commits

**Success Criteria**:
- ✅ ARC runners operational and autoscaling
- ✅ CI workflows running on all PRs
- ✅ CD auto-deploys to cluster
- ✅ Branch protection rules enforced

**Estimated Time**: 5-6 days

**Branch**: `feat/cicd-pipeline` → PR to `dev`

---

### Phase 4.3: Operational Runbooks

**Tasks**:
- [ ] Create service-specific runbooks
  - Ollama troubleshooting
  - LiteLLM debugging
  - Open WebUI issues
  - n8n workflow failures
- [ ] Add automation scripts
  - Model sync automation
  - Secret rotation automation
  - Health check automation
- [ ] Build Slack/webhook integrations
  - Alert on service down
  - Alert on sync failures
  - Daily health reports
- [ ] Update OPERATIONS.md
  - Add troubleshooting flowcharts
  - Include common error codes
  - Link to runbooks

**Success Criteria**:
- ✅ Runbook for each major service
- ✅ 5+ new automation scripts
- ✅ Alerts integrated with Slack
- ✅ OPERATIONS.md comprehensive

**Estimated Time**: 3-4 days

**Branch**: `docs/operational-runbooks` → PR to `dev`

---

## Phase 5: Developer Experience (Week 9-10)

**Goal**: Make development faster, easier, more enjoyable

### Phase 5.1: Local Development Environment

**Tasks**:
- [ ] Create local k3d/kind setup
  - Minikube alternative for laptop dev
  - Pre-configured with core services
  - Fast iteration without homelab
- [ ] Add devcontainer configuration
  - VSCode Remote Containers support
  - Pre-installed tools (kubectl, helm, argocd)
  - Environment variables preconfigured
- [ ] Build local testing scripts
  - Deploy single service locally
  - Mock external dependencies
  - Fast feedback loop
- [ ] Document local setup
  - Step-by-step local cluster setup
  - Troubleshooting local issues
  - Differences from production

**Success Criteria**:
- ✅ k3d cluster boots in < 2 minutes
- ✅ Devcontainer ready to use
- ✅ Local testing scripts functional
- ✅ Local setup docs complete

**Estimated Time**: 4-5 days

**Branch**: `feat/local-dev-env` → PR to `dev`

---

### Phase 5.2: Documentation Enhancements

**Tasks**:
- [ ] Add architecture diagrams
  - C4 model (Context, Container, Component, Code)
  - Network topology diagram
  - Data flow diagrams
- [ ] Create video tutorials
  - Quick start walkthrough
  - Deployment procedures
  - Troubleshooting common issues
- [ ] Build interactive docs
  - API explorer (Swagger/Redoc)
  - Workflow visualization
  - Live cluster status dashboard
- [ ] Improve INDEX.md
  - Add more quick references
  - Include FAQ section
  - Link to external resources

**Success Criteria**:
- ✅ 5+ architecture diagrams
- ✅ 3+ video tutorials published
- ✅ API docs auto-generated
- ✅ INDEX.md has FAQ and quick refs

**Estimated Time**: 3-4 days

**Branch**: `docs/enhancements` → PR to `dev`

---

### Phase 5.3: Testing & Quality

**Tasks**:
- [ ] Expand pytest test suite
  - Unit tests for all Python agents
  - Integration tests for API endpoints
  - End-to-end workflow tests
- [ ] Add Helm chart tests
  - helm test for each chart
  - Smoke tests post-deployment
  - Cleanup after tests
- [ ] Enable mutation testing
  - Test quality validation
  - Coverage reports
  - Badge in README
- [ ] Set up continuous testing
  - Scheduled test runs (nightly)
  - Report failures to Slack
  - Track test trends over time

**Success Criteria**:
- ✅ 80%+ test coverage for Python code
- ✅ All Helm charts have tests
- ✅ Mutation score > 70%
- ✅ Nightly test runs automated

**Estimated Time**: 5-6 days

**Branch**: `feat/testing-quality` → PR to `dev`

---

## Phase 6: Advanced Features (Week 11-12)

**Goal**: Cutting-edge AI capabilities, experimentation

### Phase 6.1: Model Fine-Tuning

**Tasks**:
- [ ] Set up fine-tuning infrastructure
  - Deploy Axolotl or Ludwig
  - Configure GPU resources
  - Prepare training datasets
- [ ] Create fine-tuning workflows
  - Dataset preparation pipeline
  - Training job submission
  - Model evaluation and deployment
- [ ] Document fine-tuning process
  - Supported base models
  - Dataset requirements
  - Best practices and tips

**Success Criteria**:
- ✅ Fine-tuning infrastructure operational
- ✅ 1+ custom model fine-tuned and deployed
- ✅ Fine-tuning documentation complete

**Estimated Time**: 6-7 days

**Branch**: `feat/model-fine-tuning` → PR to `dev`

---

### Phase 6.2: Multi-Cluster Support (Future)

**Tasks**:
- [ ] Design multi-cluster architecture
  - Federation vs. mirroring
  - Cross-cluster service discovery
  - Data replication strategy
- [ ] Implement ArgoCD ApplicationSet
  - Cluster generators
  - Templated deployments
  - Env-specific overrides
- [ ] Test edge deployments
  - Raspberry Pi cluster (ana-pi)
  - ARM64 workloads
  - Limited resource scenarios

**Success Criteria**:
- ✅ Multi-cluster design documented
- ✅ ApplicationSet deploying to 2+ clusters
- ✅ Edge deployment tested on Pi

**Estimated Time**: 7-8 days

**Branch**: `feat/multi-cluster` → PR to `dev`

---

## Git Workflow Enforcement

### Branch Strategy

```
main (production, stable releases only)
  ↑
  │ PR only (manual approval required)
  │
dev (integration branch, all features merge here)
  ↑
  │ PR with CI checks
  │
feature/* (new features, created from dev)
fix/*     (bug fixes, created from dev)
docs/*    (documentation, created from dev)
```

### Workflow Rules

**Creating Feature Branches**:
```bash
# Always branch from dev
git checkout dev
git pull origin dev
git checkout -b feature/your-feature-name

# Work on feature
git add .
git commit -m "feat: add feature description"

# Push and create PR to dev
git push -u origin feature/your-feature-name
gh pr create --base dev --title "feat: add feature description"
```

**Merging to dev**:
- ✅ Require PR approval (1+ reviewers)
- ✅ Require passing CI checks (validation, tests)
- ✅ Require conventional commit format
- ✅ Squash merge to keep history clean

**Merging to main**:
- ✅ Only from dev branch (no direct commits)
- ✅ Require manual approval from maintainer
- ✅ Require all tests passing
- ✅ Tag with semantic version (vX.Y.Z)

### Branch Protection (GitHub Settings)

**For `main` branch**:
```yaml
protection:
  required_pull_request_reviews:
    required_approving_review_count: 1
  required_status_checks:
    strict: true
    checks:
      - "validate-helm"
      - "validate-manifests"
      - "pytest"
  enforce_admins: true
  restrictions:
    users: []
    teams: ["maintainers"]
```

**For `dev` branch**:
```yaml
protection:
  required_pull_request_reviews:
    required_approving_review_count: 1
  required_status_checks:
    strict: true
    checks:
      - "validate-helm"
      - "validate-manifests"
  enforce_admins: false
```

**Implementation**:
```bash
# Set up branch protection via GitHub CLI
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --input .github/branch-protection-main.json

gh api repos/:owner/:repo/branches/dev/protection \
  --method PUT \
  --input .github/branch-protection-dev.json
```

---

## Success Metrics

### Phase 1 (Stabilization)
- ✅ Service Availability: 100% uptime for all core services
- ✅ Pod Health: Zero non-running pods (except completed jobs)
- ✅ Response Times: < 2s for UI, < 500ms for API
- ✅ Error Rate: < 0.1% for all endpoints

### Phase 2 (SSO & Security)
- ✅ SSO Coverage: 100% of external services
- ✅ Security Score: Zero critical CVEs
- ✅ Policy Compliance: 100% Kyverno policy adherence
- ✅ Secret Age: All secrets < 30 days old

### Phase 3 (AI Capabilities)
- ✅ Model Count: 30+ models available
- ✅ RAG Accuracy: > 85% relevance in retrieval
- ✅ Workflow Reliability: > 95% successful executions
- ✅ API Latency: < 3s for model inference

### Phase 4 (Operations)
- ✅ Backup Success Rate: 100% daily backups
- ✅ Recovery Time: < 1 hour full cluster restore
- ✅ CI/CD Speed: < 10 minutes PR validation
- ✅ Alert Response Time: < 15 minutes MTTD (Mean Time To Detect)

### Phase 5 (Developer Experience)
- ✅ Local Setup Time: < 10 minutes
- ✅ Test Coverage: > 80% for Python code
- ✅ Documentation Completeness: 100% API endpoints documented
- ✅ Onboarding Time: < 1 day for new developers

### Phase 6 (Advanced Features)
- ✅ Custom Models: 3+ fine-tuned models deployed
- ✅ Multi-Cluster: 2+ clusters operational
- ✅ Edge Deployment: Pi cluster running

---

## Timeline Summary

| Phase | Duration | Start Date | End Date | Key Deliverables |
|-------|----------|------------|----------|------------------|
| **Phase 1: Stabilization** | 2 weeks | Week 1 | Week 2 | All services healthy, GPU working |
| **Phase 2: SSO & Security** | 2 weeks | Week 3 | Week 4 | Complete SSO, hardened security |
| **Phase 3: AI Capabilities** | 2 weeks | Week 5 | Week 6 | RAG, more models, workflows |
| **Phase 4: Operations** | 2 weeks | Week 7 | Week 8 | Backup/DR, CI/CD, runbooks |
| **Phase 5: Developer Experience** | 2 weeks | Week 9 | Week 10 | Local dev, docs, testing |
| **Phase 6: Advanced Features** | 2 weeks | Week 11 | Week 12 | Fine-tuning, multi-cluster |

**Total**: 12 weeks (~3 months)

**Checkpoints**:
- Week 2: Phase 1 demo (stable platform)
- Week 4: Phase 2 demo (secured platform)
- Week 6: Phase 3 demo (enhanced AI)
- Week 8: Phase 4 demo (automated ops)
- Week 10: Phase 5 demo (great DevEx)
- Week 12: Phase 6 demo (advanced features) + v1.0 release

---

## Risk Management

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| GPU operator issues persist | High | Medium | Fallback to CPU-only, consult NVIDIA docs |
| Storage capacity exhausted | High | Low | Monitor Longhorn usage, add nodes if needed |
| Security vulnerability discovered | High | Medium | Rapid patching process, CVE monitoring |
| Performance degradation | Medium | Medium | Regular load testing, auto-scaling |
| Team capacity constraints | Medium | High | Prioritize ruthlessly, defer Phase 6 if needed |
| Dependency breaking changes | Low | High | Pin versions, test upgrades in staging |

---

## Next Steps (Immediate Action)

1. **Review this roadmap** with team/stakeholders
2. **Prioritize Phase 1.1** (GPU workload enablement) as highest priority
3. **Create feature branches** from `dev` for each phase
4. **Set up branch protection** for `main` and `dev`
5. **Schedule Phase 1 kickoff** (target: tomorrow)

---

**Questions? Feedback?** Open an issue or discuss in #self-hosted-ai Slack channel.

**Last Updated**: 2026-02-06 by Claude Sonnet 4.5
