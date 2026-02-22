# Self-Hosted AI Platform - Manual Test Checklist

**Purpose**: UI/UX verification that cannot be fully automated
**When to Run**: After major deployments, before marking release as stable
**Time Estimate**: 45-60 minutes for full checklist

---

## Instructions

- Execute each test in order (dependencies flow top to bottom)
- Mark each test: PASS / FAIL / SKIP / N/A
- Record issues in the Notes column
- If a section fails, continue testing remaining sections
- Screenshot failures for documentation

---

## 1. Infrastructure Prerequisites

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 1.1 | `kubectl get nodes` shows all nodes Ready | 2 nodes: akula-prime, homelab | | |
| 1.2 | `kubectl get pods -A \| grep -v Running` shows no failing pods | No non-Running pods (except Completed jobs) | | |
| 1.3 | ArgoCD dashboard loads at https://argocd.vectorweight.com | Login page or dashboard visible | | |
| 1.4 | All ArgoCD apps show Synced/Healthy | No Degraded or Unknown apps | | |

---

## 2. Authentication & SSO

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 2.1 | Navigate to https://ai.vectorweight.com | Login page loads with local + Keycloak options | | |
| 2.2 | Click "Sign in with Keycloak" | Redirects to Keycloak login page | | |
| 2.3 | Login with Keycloak credentials (kang) | Redirects back to Open WebUI, logged in | | |
| 2.4 | Verify username shown in UI | Shows "kang" or configured display name | | |
| 2.5 | Login with local admin credentials | Admin access with full permissions | | |
| 2.6 | Navigate to https://n8n.vectorweight.com | Login page or SSO redirect | | |
| 2.7 | Navigate to https://grafana.vectorweight.com | Grafana dashboard loads | | |

---

## 3. Open WebUI - Chat Interface

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 3.1 | Model dropdown shows available models | Multiple models listed (qwen2.5-coder, phi4, llama3.1, etc.) | | |
| 3.2 | Select qwen2.5-coder:14b model | Model selected, shown in header | | |
| 3.3 | Send message: "Hello, what model are you?" | Response within 30s mentioning Qwen | | |
| 3.4 | Send follow-up: "What did I just ask you?" | Maintains conversation context | | |
| 3.5 | Switch to phi4:latest model | Model changes, new conversation | | |
| 3.6 | Send coding prompt: "Write a Python fibonacci function" | Returns valid Python code with formatting | | |
| 3.7 | New conversation button works | Starts fresh conversation, clears history | | |
| 3.8 | Conversation history sidebar shows previous chats | Previous conversations listed | | |
| 3.9 | Click previous conversation to resume | Loads conversation with full history | | |
| 3.10 | Delete a conversation | Conversation removed from history | | |

---

## 4. Open WebUI - Web Search Integration

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 4.1 | Enable web search toggle in chat | Search icon/toggle activates | | |
| 4.2 | Ask: "What is the latest version of Python?" | Response includes web search results with citations | | |
| 4.3 | Verify search results source | Sources show SearXNG results | | |
| 4.4 | Navigate to https://search.vectorweight.com | SearXNG search page loads | | |
| 4.5 | Perform direct search in SearXNG | Returns search results | | |

---

## 5. Open WebUI - RAG (Document Upload)

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 5.1 | Upload a PDF document via chat | Document processed, embedding generated | | |
| 5.2 | Ask question about uploaded document | Response references document content | | |
| 5.3 | Upload a text file | File processed successfully | | |
| 5.4 | Paste a URL in chat | URL content fetched and processed | | |

---

## 6. Open WebUI - Vision & Multimodal

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 6.1 | Switch to llava:13b model | Vision model selected | | |
| 6.2 | Upload an image in chat | Image preview shown | | |
| 6.3 | Ask: "Describe this image" | Model describes image content accurately | | |

---

## 7. Open WebUI - Tools & Functions

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 7.1 | Navigate to Admin > Functions | Functions management page loads | | |
| 7.2 | List available tools | Pre-configured tools shown | | |
| 7.3 | Test a tool in chat (if configured) | Tool executes and returns result | | |

---

## 8. Open WebUI - Admin Settings

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 8.1 | Navigate to Admin > Settings | Settings page loads | | |
| 8.2 | Verify Ollama connections configured | Two Ollama URLs shown (GPU + CPU) | | |
| 8.3 | Verify default model set | qwen2.5-coder:14b as default | | |
| 8.4 | Verify signup disabled | Signup toggle is off | | |
| 8.5 | Verify evaluation arena configured | Arena models listed | | |

---

## 9. LiteLLM API Gateway

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 9.1 | `curl https://llm.vectorweight.com/health` | Returns 200 with health info | | |
| 9.2 | `curl https://llm.vectorweight.com/v1/models` | Lists available models | | |
| 9.3 | Send chat completion via curl | Returns OpenAI-format response | | |
| 9.4 | Verify fallback: request unavailable model | Falls back to CPU model | | |

---

## 10. n8n Workflow Automation

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 10.1 | Navigate to https://n8n.vectorweight.com | n8n editor loads | | |
| 10.2 | List workflows | Pre-configured workflows visible | | |
| 10.3 | Open agentic-reasoning workflow | Workflow nodes display correctly | | |
| 10.4 | Activate a test workflow | Workflow activates without errors | | |
| 10.5 | Trigger webhook endpoint | Workflow executes and returns result | | |
| 10.6 | Check workflow execution history | Execution logs available | | |

---

## 11. Monitoring & Observability

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 11.1 | Navigate to https://grafana.vectorweight.com | Grafana loads | | |
| 11.2 | Verify Prometheus data source connected | Green checkmark on data source | | |
| 11.3 | Open a pre-configured dashboard | Dashboard renders with data | | |
| 11.4 | Navigate to Explore > Tempo | Trace search interface loads | | |
| 11.5 | Search for recent traces | Traces from LiteLLM/Open WebUI visible | | |
| 11.6 | Navigate to https://prometheus.vectorweight.com | Prometheus UI loads | | |
| 11.7 | Query `up` metric | Shows all scrape targets | | |

---

## 12. ArgoCD GitOps

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 12.1 | Login to ArgoCD dashboard | Dashboard with app topology | | |
| 12.2 | View application tree | All apps visible with status | | |
| 12.3 | Click on an application | App details, resources, events shown | | |
| 12.4 | Verify sync status on all apps | Most apps show Synced | | |
| 12.5 | Check for any Degraded apps | No degraded apps (or known exceptions) | | |

---

## 13. MCP Server Integration

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 13.1 | MCP servers pod is Running | `kubectl get pods -n self-hosted-ai -l app=mcp-servers` | | |
| 13.2 | Filesystem MCP server responds | Tool call returns file listing | | |
| 13.3 | Git MCP server responds | Tool call returns git status | | |
| 13.4 | Kubernetes MCP server responds | Tool call returns namespace info | | |
| 13.5 | MCP tools visible in Open WebUI (if configured) | Tools listed in chat interface | | |

---

## 14. Performance Spot Checks

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 14.1 | Time a simple chat response (8B model) | < 15 seconds for short reply | | |
| 14.2 | Time a coding prompt (14B model) | < 30 seconds for short function | | |
| 14.3 | Check GPU utilization during inference | `nvidia-smi` shows GPU active | | |
| 14.4 | Check no pods near memory limits | `kubectl top pods -A --sort-by=memory` | | |
| 14.5 | Check PVC storage usage | No PVCs above 80% capacity | | |

---

## 15. Security Spot Checks

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 15.1 | Verify HTTPS on all external URLs | No HTTP-only access to services | | |
| 15.2 | Try accessing admin APIs without auth | Returns 401/403 | | |
| 15.3 | Verify no default/weak passwords | All services use configured passwords | | |
| 15.4 | Check certificate validity | `kubectl get certificates -A` all True | | |

---

## Test Summary

| Section | Total | Pass | Fail | Skip | N/A |
|---------|-------|------|------|------|-----|
| 1. Infrastructure | 4 | | | | |
| 2. Authentication | 7 | | | | |
| 3. Chat Interface | 10 | | | | |
| 4. Web Search | 5 | | | | |
| 5. RAG | 4 | | | | |
| 6. Vision | 3 | | | | |
| 7. Tools | 3 | | | | |
| 8. Admin Settings | 5 | | | | |
| 9. LiteLLM API | 4 | | | | |
| 10. n8n | 6 | | | | |
| 11. Monitoring | 7 | | | | |
| 12. ArgoCD | 5 | | | | |
| 13. MCP Servers | 5 | | | | |
| 14. Performance | 5 | | | | |
| 15. Security | 4 | | | | |
| **TOTAL** | **77** | | | | |

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | | | |
| Reviewer | | | |

---

**Notes / Issues Found:**

(Record any issues, observations, or follow-up items here)
