# Self-Hosted AI Platform - End-to-End Test Strategy

**Version**: 1.0
**Date**: 2026-02-22
**Author**: Claude Code (Opus 4.6)
**Status**: Implementation Ready

---

## 1. Testing Architecture Overview

```
                        TEST PYRAMID
                    ┌─────────────────┐
                    │   End-to-End    │  ~10 tests
                    │   (Full flows)  │  Manual + Auto
                    ├─────────────────┤
                    │  Integration    │  ~40 tests
                    │  (Service mesh) │  Automated
                    ├─────────────────┤
                    │   API Tests     │  ~50 tests
                    │  (Endpoints)    │  Automated
                    ├─────────────────┤
                    │  Config Valid.  │  ~30 tests
                    │  (K8s/Helm)     │  Automated
                    ├─────────────────┤
                    │   Unit Tests    │  ~20 tests
                    │  (Python agents)│  Automated
                    └─────────────────┘
```

### Test Categories

| Category | Count | Framework | Runtime | Environment |
|----------|-------|-----------|---------|-------------|
| Unit Tests | ~20 | pytest | <30s | Local (mocked) |
| Configuration Validation | ~30 | pytest + kubectl | <60s | Cluster required |
| API Tests | ~50 | pytest + httpx | <120s | Cluster required |
| Integration Tests | ~40 | pytest + httpx | <300s | Cluster required |
| Security Tests | ~15 | pytest + kubectl | <60s | Cluster required |
| Performance Tests | ~10 | pytest + httpx | <600s | Cluster required |
| End-to-End Tests | ~10 | Manual + pytest | Variable | Cluster required |

**Total**: ~175 test cases

---

## 2. Test Execution Layers

### Layer 1: Offline Validation (No Cluster Required)

These run locally without a Kubernetes cluster.

- **Unit tests**: Python agent framework (`tests/test_core_*.py`)
- **Helm lint**: `helm lint helm/*/`
- **YAML validation**: Schema validation for configs
- **Static analysis**: Ruff, mypy
- **Secret detection**: detect-secrets

### Layer 2: Cluster Infrastructure (Cluster Required)

Validates Kubernetes resources exist and are healthy.

- **Node health**: Nodes Ready, resources available
- **Namespace existence**: All expected namespaces created
- **Pod health**: All pods Running/Ready
- **PVC status**: Persistent volumes Bound
- **ArgoCD sync**: All applications Synced/Healthy
- **Certificate status**: TLS certificates valid
- **Secret existence**: Required secrets present
- **Resource quotas**: Quotas applied correctly

### Layer 3: Service APIs (Cluster Required)

Validates individual service endpoints respond correctly.

- **Health endpoints**: `/health`, `/healthz`, `/api/health`
- **API authentication**: Bearer tokens, API keys
- **Model availability**: Ollama models loaded
- **Database connectivity**: PostgreSQL, Redis
- **Search functionality**: SearXNG queries

### Layer 4: Integration (Cluster Required)

Validates services work together correctly.

- **Open WebUI -> Ollama**: Chat completion flow
- **Open WebUI -> SearXNG**: Web search from chat
- **LiteLLM -> Ollama GPU/CPU**: Model routing and fallback
- **LiteLLM -> Redis**: Response caching
- **LiteLLM -> PostgreSQL**: Spend tracking
- **n8n -> LiteLLM**: Workflow AI calls
- **n8n -> MCP servers**: Tool integration
- **Keycloak -> OAuth2-proxy**: SSO authentication
- **Open WebUI -> Keycloak**: OIDC login
- **Traefik -> all services**: Ingress routing
- **cert-manager -> Traefik**: TLS termination
- **OTel -> Tempo**: Trace ingestion

### Layer 5: End-to-End Scenarios

Validates complete user workflows.

- **New user login**: Keycloak SSO -> Open WebUI
- **Chat conversation**: Login -> Select model -> Send message -> Receive response
- **Web search chat**: Send question -> SearXNG search -> Augmented response
- **Document RAG**: Upload document -> Ask question -> RAG response
- **n8n workflow**: Trigger webhook -> AI processing -> Result
- **Image generation**: Prompt -> ComfyUI -> Generated image (when deployed)
- **Model switching**: GPU model -> Fallback to CPU model

---

## 3. Framework & Tooling

### Primary Framework

```
pytest 8.3+
├── pytest-asyncio     # Async test support
├── pytest-httpx       # HTTP client mocking
├── pytest-cov         # Coverage reporting
├── pytest-timeout     # Prevent hanging tests
├── pytest-xdist       # Parallel execution
└── pytest-html        # HTML report generation
```

### Test Dependencies

```
httpx              # Async HTTP client
kubernetes         # K8s API client
pyyaml             # YAML parsing
rich               # Console output
```

### Test Directory Structure

```
tests/
├── conftest.py                 # Shared fixtures, cluster config
├── test_core_base.py           # Existing: Agent unit tests
├── test_core_task.py           # Existing: Task unit tests
├── __init__.py
│
├── platform/                   # Platform validation tests
│   ├── __init__.py
│   ├── conftest.py             # Platform fixtures (cluster connection)
│   ├── test_cluster_health.py  # Node, namespace, pod health
│   ├── test_argocd_sync.py     # ArgoCD application sync state
│   ├── test_config_validation.py # Helm, YAML, config correctness
│   ├── test_certificates.py    # TLS cert validity
│   ├── test_secrets.py         # Required secrets present
│   └── test_resource_quotas.py # Quotas and limit ranges
│
├── api/                        # API endpoint tests
│   ├── __init__.py
│   ├── conftest.py             # API fixtures (httpx clients)
│   ├── test_ollama_api.py      # Ollama health, models, generate
│   ├── test_litellm_api.py     # LiteLLM proxy, models, chat
│   ├── test_openwebui_api.py   # Open WebUI health, auth, models
│   ├── test_searxng_api.py     # SearXNG search
│   ├── test_n8n_api.py         # n8n webhooks, workflows
│   ├── test_keycloak_api.py    # Keycloak realm, OIDC
│   ├── test_mcp_api.py         # MCP server endpoints
│   └── test_monitoring_api.py  # Grafana, Prometheus, Tempo
│
├── integration/                # Service integration tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_inference_pipeline.py    # Full inference: LiteLLM->Ollama
│   ├── test_rag_pipeline.py          # Document upload -> RAG query
│   ├── test_sso_flow.py              # Keycloak->OAuth2->Services
│   ├── test_observability.py         # Traces, metrics, logs
│   └── test_model_routing.py         # GPU/CPU fallback, load balancing
│
├── security/                   # Security validation tests
│   ├── __init__.py
│   ├── test_tls_validation.py  # TLS certificates, no insecureSkipVerify
│   ├── test_pod_security.py    # PSS baseline compliance
│   ├── test_network_policy.py  # Default deny, allowed traffic
│   ├── test_rbac.py            # Service account permissions
│   └── test_secrets_security.py # No plaintext secrets
│
├── performance/                # Performance benchmarks
│   ├── __init__.py
│   ├── test_inference_latency.py  # Model response times
│   ├── test_api_throughput.py     # Requests per second
│   └── test_resource_usage.py     # CPU/memory utilization
│
└── e2e/                        # End-to-end scenarios
    ├── __init__.py
    ├── test_chat_workflow.py       # Full chat conversation
    ├── test_search_workflow.py     # Search-augmented chat
    └── test_multi_model.py         # Model switching, fallback
```

---

## 4. Pass/Fail Criteria

### Deployment Readiness Gate

A deployment is considered ready when ALL of the following pass:

| Gate | Criteria | Blocking |
|------|----------|----------|
| **G1: Infrastructure** | All nodes Ready, all critical pods Running | Yes |
| **G2: ArgoCD** | All applications Synced, no Degraded apps | Yes |
| **G3: Certificates** | Wildcard TLS cert valid and not expiring <7d | Yes |
| **G4: Secrets** | All required secrets present in namespaces | Yes |
| **G5: Health Checks** | All service health endpoints return 200 | Yes |
| **G6: Inference** | At least 1 GPU model responds to prompts | Yes |
| **G7: API** | LiteLLM, Open WebUI, Ollama APIs functional | Yes |
| **G8: Security** | No plaintext secrets, TLS valid, PSS compliant | Warning |
| **G9: Performance** | p95 inference latency <30s for 8B model | Warning |
| **G10: Integration** | Open WebUI can complete a chat via LiteLLM | Yes |

### Test Severity Levels

- **CRITICAL**: Platform unusable if failing (infrastructure, core APIs)
- **HIGH**: Major feature broken (SSO, model routing, search)
- **MEDIUM**: Degraded experience (slow inference, missing metrics)
- **LOW**: Cosmetic or nice-to-have (documentation links, non-critical MCP)

---

## 5. Configuration & Environment

### Environment Variables

```bash
# Cluster connectivity
KUBECONFIG=~/.kube/config
CLUSTER_CONTEXT=default

# Service endpoints (internal, via port-forward or ClusterIP)
OLLAMA_GPU_URL=http://ollama-gpu.gpu-workloads:11434
OLLAMA_CPU_URL=http://ollama.ai-services:11434
LITELLM_URL=http://litellm.self-hosted-ai:4000
OPENWEBUI_URL=http://open-webui.self-hosted-ai:8080
SEARXNG_URL=http://searxng.self-hosted-ai:8080
N8N_URL=http://n8n.automation:5678
KEYCLOAK_URL=http://keycloak.auth:8080
MCP_URL=http://mcp-servers.self-hosted-ai:8000
GRAFANA_URL=http://grafana.monitoring:80
PROMETHEUS_URL=http://prometheus.monitoring:9090

# External endpoints (via Traefik ingress)
PLATFORM_DOMAIN=vectorweight.com
OPENWEBUI_EXTERNAL=https://ai.vectorweight.com
LITELLM_EXTERNAL=https://llm.vectorweight.com
ARGOCD_EXTERNAL=https://argocd.vectorweight.com
N8N_EXTERNAL=https://n8n.vectorweight.com
GRAFANA_EXTERNAL=https://grafana.vectorweight.com

# Test credentials
LITELLM_MASTER_KEY=<from sealed secret>
WEBUI_ADMIN_EMAIL=admin@vectorweight.com
WEBUI_ADMIN_PASSWORD=<from sealed secret>

# Test settings
TEST_TIMEOUT=300
TEST_MODEL=llama3.1:8b    # Fast model for testing
TEST_GPU_MODEL=qwen2.5-coder:14b
SKIP_SLOW_TESTS=false
SKIP_GPU_TESTS=false
```

### pytest Markers

```ini
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (no cluster required)",
    "platform: Cluster infrastructure validation",
    "api: API endpoint tests",
    "integration: Service integration tests",
    "security: Security validation tests",
    "performance: Performance benchmark tests",
    "e2e: End-to-end workflow tests",
    "gpu: Tests requiring GPU access",
    "slow: Tests taking >30 seconds",
    "critical: Tests for deployment gate",
]
```

---

## 6. Reporting & Metrics

### Test Report Template

```
================================================================
  SELF-HOSTED AI PLATFORM - TEST REPORT
  Date: YYYY-MM-DD HH:MM
  Branch: dev
  Cluster: akula-prime + homelab
================================================================

SUMMARY
  Total:    175
  Passed:   170
  Failed:   3
  Skipped:  2
  Duration: 8m 42s

DEPLOYMENT GATES
  [PASS] G1: Infrastructure ................ 12/12
  [PASS] G2: ArgoCD Sync ................... 30/30
  [PASS] G3: Certificates .................. 3/3
  [PASS] G4: Secrets ....................... 15/15
  [PASS] G5: Health Checks ................. 10/10
  [PASS] G6: Inference ..................... 5/5
  [FAIL] G7: API Endpoints ................. 8/10
  [PASS] G8: Security ...................... 12/12
  [WARN] G9: Performance ................... 3/5
  [PASS] G10: Integration .................. 8/8

FAILURES
  [HIGH] test_litellm_api::test_chat_completion
    Error: Connection refused to litellm.self-hosted-ai:4000
    Impact: LiteLLM proxy not routing requests

  [MEDIUM] test_api_throughput::test_concurrent_requests
    Expected: >10 req/s  Actual: 7 req/s
    Impact: Performance below baseline

RECOMMENDATIONS
  1. Check LiteLLM pod logs: kubectl logs -n self-hosted-ai deploy/litellm
  2. Verify litellm-secret exists in self-hosted-ai namespace
  3. Consider increasing LiteLLM resources for throughput target

================================================================
```

### Coverage Targets

| Category | Target | Minimum |
|----------|--------|---------|
| Unit Tests | 80% | 60% |
| API Endpoints | 100% of health endpoints | 90% |
| Integration Paths | 100% of critical paths | 80% |
| Security Controls | 100% | 100% |
| Services Covered | 100% of deployed services | 90% |

---

## 7. Integration Matrix

### Service Dependency Map (What Tests What)

```
┌──────────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│              │ Ollama   │ LiteLLM  │ OpenWebUI│ SearXNG  │ n8n      │ Keycloak │
│              │ GPU/CPU  │          │          │          │          │          │
├──────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ Ollama GPU   │    -     │  route   │  direct  │          │  via API │          │
│ Ollama CPU   │ fallback │  route   │  direct  │          │  via API │          │
│ LiteLLM      │  uses    │    -     │  proxied │          │  uses    │          │
│ Open WebUI   │  calls   │  calls   │    -     │  calls   │          │  SSO     │
│ SearXNG      │          │          │ searched │    -     │          │          │
│ n8n          │          │  calls   │          │  calls   │    -     │  SSO     │
│ PostgreSQL   │          │  stores  │  stores  │          │  stores  │  stores  │
│ Redis        │          │  caches  │          │          │          │          │
│ Keycloak     │          │          │  OIDC    │          │  OIDC    │    -     │
│ Traefik      │          │  ingress │  ingress │  ingress │  ingress │  ingress │
│ cert-manager │          │  TLS     │  TLS     │  TLS     │  TLS     │  TLS     │
└──────────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

### Critical Path Tests

1. **Inference Path**: Client -> Traefik -> LiteLLM -> Ollama GPU -> Response
2. **UI Path**: Browser -> Traefik -> Open WebUI -> Ollama -> Response
3. **Auth Path**: Browser -> Traefik -> Open WebUI -> Keycloak -> JWT -> Access
4. **Search Path**: Open WebUI -> SearXNG -> DuckDuckGo -> RAG -> Response
5. **Monitoring Path**: Service -> OTel Collector -> Tempo -> Grafana

---

## 8. Maintenance Strategy

### Test Maintenance

- **On new service**: Add API health test + integration test + update matrix
- **On config change**: Run `test:platform` to validate
- **On model change**: Run `test:api` to verify model availability
- **Weekly**: Full test suite execution, review flaky tests
- **Monthly**: Review performance baselines, update thresholds

### Flaky Test Policy

- Tests that fail intermittently get `@pytest.mark.flaky(reruns=3)`
- After 3 consecutive flaky failures, investigate root cause
- Network-dependent tests use exponential backoff retries
- Inference tests allow variance in response content (check structure, not exact text)

### Version Pinning

Test infrastructure versions are pinned in `pyproject.toml` to prevent surprise breakage.
Update test dependencies quarterly, in sync with platform dependency updates.

---

## 9. CI/CD Integration

### Taskfile Targets

```yaml
test:unit:        # Run unit tests only (no cluster)
test:platform:    # Validate cluster infrastructure
test:api:         # Test all API endpoints
test:integration: # Test service integrations
test:security:    # Security validation
test:performance: # Performance benchmarks
test:e2e:         # End-to-end scenarios
test:all:         # Complete test suite
test:critical:    # Deployment gate tests only
test:report:      # Generate HTML report
```

### Pre-commit Integration

```yaml
# Run on every commit
- task validate:helm
- task test:unit

# Run before push
- task test:critical
```

### CI Pipeline (GitHub Actions)

```
push to dev
  ├── Helm lint + Unit tests (1 min)
  ├── Platform validation (2 min, needs cluster)
  └── Full test suite (10 min, needs cluster)
        ├── API tests
        ├── Integration tests
        ├── Security tests
        └── Generate report artifact
```

---

## 10. Manual Test Checklist

See `docs/MANUAL_TEST_CHECKLIST.md` for the complete manual UI/UX verification checklist.

Key areas requiring manual verification:
- Open WebUI chat interface responsiveness
- Model selection dropdown populated
- Keycloak SSO login flow (browser redirect)
- n8n workflow editor functionality
- Grafana dashboard rendering
- ArgoCD application topology view
