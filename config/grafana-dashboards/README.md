# Grafana Dashboards for Self-Hosted AI Platform

This directory contains Grafana dashboard definitions provisioned via ConfigMaps.

## Available Dashboards

### LLM Request Tracing (`llm-tracing-dashboard.json`)

**Purpose**: Monitor distributed traces across the AI inference pipeline (Open WebUI → LiteLLM → Ollama)

**Access**: https://grafana.vectorweight.com → Dashboards → Tracing folder → "LLM Request Tracing"

**Panels**:
1. **AI Service Topology** - Node graph showing service dependencies and call patterns
2. **Request Rate** - Traces per second for litellm and open-webui
3. **LiteLLM Latency Percentiles** - p50, p95, p99 latencies over time
4. **Error Rate (5xx)** - Percentage of failed requests
5. **Slow Requests (> 5s)** - Table of traces exceeding 5 second duration
6. **Recent Traces** - Last 50 traces with metadata

**Variables**:
- `$interval` - Time range for rate calculations (1m, 5m, 15m, 1h)

---

## Example TraceQL Queries

These queries can be used in Grafana Explore (Tempo datasource) for debugging.

### Find Slow Requests

```traceql
# Requests taking longer than 5 seconds
{service.name="litellm"} | duration > 5s

# Requests taking longer than 10 seconds on specific model
{service.name="litellm" && resource.model="qwen2.5-coder:14b"} | duration > 10s
```

### Find Errors

```traceql
# All errors in LiteLLM
{service.name="litellm" && status=error}

# HTTP 5xx errors
{service.name="litellm" && http.status_code >= 500}

# Specific error messages
{service.name="litellm" && status=error} | select(span.error_message)
```

### Filter by Model

```traceql
# All requests for a specific model
{service.name="litellm" && resource.model="llama3.2:3b"}

# Slow requests on GPU models
{service.name="litellm" && resource.model=~"qwen.*"} | duration > 3s
```

### Filter by User/Session

```traceql
# Requests from specific user (if user ID propagated)
{service.name="open-webui" && user.id="admin"}

# Requests in specific session
{service.name="open-webui" && session.id="abc123"}
```

### Time-based Queries

```traceql
# Requests in last hour with high latency
{service.name="litellm"} | duration > 5s && startTime > 1h

# Errors in last 30 minutes
{service.name="litellm" && status=error} && startTime > 30m
```

### Span-level Filtering

```traceql
# Find database queries in traces
{service.name="open-webui"} && span.name =~ ".*SELECT.*"

# Find Ollama inference calls
{service.name="litellm"} && span.name =~ ".*ollama.*"
```

### Aggregations

```traceql
# Count traces per service
{} | count() by service.name

# Average duration by model
{service.name="litellm"} | avg(duration) by resource.model

# Error rate by service
{status=error} | rate() by service.name
```

---

## Common Debugging Scenarios

### Scenario 1: Chat Request is Slow

**Steps**:
1. Go to Grafana → Explore → Tempo
2. Query: `{service.name="open-webui"} | duration > 5s`
3. Click on a slow trace
4. View waterfall to identify bottleneck:
   - Long database query? → Check PostgreSQL
   - Long LiteLLM call? → Continue to LiteLLM span
   - Long Ollama inference? → Check GPU utilization

**Expected Flow**:
```
Open WebUI (user request)
  → PostgreSQL (load chat history) - ~100ms
  → LiteLLM (inference request) - ~2-10s
    → Ollama (model inference) - ~1-8s
```

### Scenario 2: High Error Rate

**Steps**:
1. Check error rate gauge on dashboard
2. Query errors: `{service.name="litellm" && status=error}`
3. Identify pattern:
   - All errors on specific model? → Model crashed
   - Errors at specific time? → Infrastructure issue
   - Errors on all requests? → Configuration problem
4. Click on error trace → View span attributes for error details

### Scenario 3: Identify Model Performance Differences

**Steps**:
1. Use Grafana Explore with aggregation:
   ```traceql
   {service.name="litellm"} | avg(duration) by resource.model
   ```
2. Compare average latencies across models
3. Identify slow models for optimization

### Scenario 4: Trace User Journey

**Steps**:
1. Find initial request trace ID from Open WebUI logs
2. Query: `{trace_id="<trace-id>"}`
3. View full trace showing:
   - User → Open WebUI → LiteLLM → Ollama
   - All database queries
   - All API calls
   - Total end-to-end latency

---

## Trace-to-Logs Correlation

Grafana supports jumping from traces to related logs:

1. In Tempo trace view, click any span
2. Click "Logs for this span" button
3. Automatically queries OpenObserve for logs matching:
   - Same service name
   - Same time range
   - Same trace ID (if propagated)

This enables end-to-end debugging: trace → identify slow span → view logs → find root cause.

---

## Dashboard Provisioning

Dashboards are auto-loaded by Grafana's sidecar container when:
1. ConfigMap has label `grafana_dashboard: "1"`
2. ConfigMap in any namespace (sidecar searches `ALL`)
3. Dashboard JSON in ConfigMap data

**Deployment**:
```bash
kubectl apply -f argocd/applications/grafana-dashboards.yaml
```

Grafana sidecar detects the ConfigMap and loads the dashboard within 60 seconds.

**Verification**:
```bash
# Check ConfigMap exists
kubectl get configmap llm-tracing-dashboard -n monitoring

# Check Grafana logs
kubectl logs -n monitoring deployment/prometheus-grafana -c grafana-sc-dashboard -f
```

---

## Metrics Used

The dashboard queries Prometheus metrics generated by Tempo's metrics generator:

| Metric | Type | Description |
|--------|------|-------------|
| `traces_spanmetrics_calls_total` | Counter | Total trace count per service |
| `traces_spanmetrics_latency_bucket` | Histogram | Latency distribution (for percentiles) |
| `traces_spanmetrics_size_total` | Histogram | Span size distribution |

These metrics are derived from traces, so no separate instrumentation needed.

---

## Adding New Dashboards

1. Create dashboard JSON in this directory
2. Create ConfigMap manifest in `argocd/applications/`:
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: my-dashboard
     namespace: monitoring
     labels:
       grafana_dashboard: "1"
     annotations:
       grafana_folder: "Custom"  # Folder name in Grafana
   data:
     my-dashboard.json: |
       { ... dashboard JSON ... }
   ```
3. Apply: `kubectl apply -f argocd/applications/my-dashboard.yaml`

---

**Troubleshooting**:
- Dashboard not appearing? Check `kubectl get configmap -n monitoring -l grafana_dashboard=1`
- Panels showing "No data"? Verify Tempo/Prometheus datasources in Grafana settings
- Queries timing out? Reduce time range or add more specific filters
