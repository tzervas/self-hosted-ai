---
title: Architecture Decision Records
description: Key architectural decisions and their rationale
---

# Architecture Decision Records

## ADR-001: Kubernetes as Platform

**Context**: Need a container orchestration platform for multi-service deployment.

**Decision**: Use k3s (lightweight Kubernetes) for single-node deployment with ability to scale.

**Rationale**: Industry standard with vast ecosystem, GitOps-native with ArgoCD, resource efficient (k3s), portable workloads.

---

## ADR-002: ArgoCD for GitOps

**Context**: Need a deployment mechanism that enforces IaC principles.

**Decision**: Use ArgoCD with App-of-Apps pattern for all deployments.

**Rationale**: Declarative Git-driven deployments, automatic drift detection, visual dashboard, sync waves for dependency ordering.

See [Sync Waves](../deployment/sync-waves.md) for deployment order details.

---

## ADR-003: LiteLLM as API Gateway

**Context**: Need unified API access to multiple LLM backends with rate limiting and routing.

**Decision**: Use LiteLLM proxy as the primary AI API gateway.

**Rationale**: OpenAI-compatible API, model routing and fallback, rate limiting and cost tracking, single endpoint for all models.

---

## ADR-004: SealedSecrets for Credential Management

**Context**: Need to store secrets in Git without exposing values.

**Decision**: Use Bitnami SealedSecrets for all Kubernetes secrets.

**Rationale**: Secrets encrypted at rest in Git, cluster-specific decryption, GitOps-compatible workflow, no external secret store dependency.

---

## ADR-005: Python + uv for Automation

**Context**: Need reliable, maintainable automation scripts.

**Decision**: Replace shell scripts with Python 3.12+ managed by uv.

**Rationale**: Type safety with mypy, better error handling, async operations for performance, rich CLI interfaces, dependency management.

---

## ADR-006: MCP for Tool Integration

**Context**: Need standardized way to expose tools to AI agents.

**Decision**: Use Model Context Protocol (MCP) for tool discovery and execution.

**Rationale**: Emerging standard (Anthropic), language-agnostic, supports multiple transports, growing ecosystem.

---

## ADR-007: Traefik for Ingress

**Context**: Need HTTP/HTTPS routing with TLS termination.

**Decision**: Use Traefik v3 as the ingress controller.

**Rationale**: Native Kubernetes integration, automatic TLS with cert-manager, middleware support, dashboard for visibility.

---

## ADR-008: Internal CA for TLS

**Context**: Need TLS everywhere but external CAs require DNS validation.

**Decision**: Use self-signed root CA with cert-manager for internal certificates.

**Rationale**: No external dependencies, instant certificate issuance, full control over trust chain, works in air-gapped environments.

---

## ADR-009: ARC for GitHub Actions CI/CD

**Context**: Need self-hosted CI/CD runners for builds, tests, and deployments.

**Decision**: Use Actions Runner Controller (ARC) with scale-to-zero runners.

**Runner Types**:

- **amd64**: Standard builds on homelab k3s cluster
- **gpu**: ML/AI workloads accessing GPU over LAN
- **arm64**: ARM builds via QEMU binfmt emulation on amd64 host

---

## ADR-010: GPU Over LAN Architecture

**Context**: GPU workstation (akula-prime) is a separate machine, not a Kubernetes node.

**Decision**: Access GPU inference via HTTP/REST over LAN rather than k8s scheduling.

**Implementation**: GPU-requiring pods use `OLLAMA_GPU_HOST=192.168.1.99:11434` environment variable. No `nvidia.com/gpu` resource requests in k8s.

---

## ADR-011: Linkerd for Service Mesh

**Context**: Need service-to-service mTLS and observability without Istio overhead.

**Decision**: Deploy Linkerd v2025.1.2 for automatic mTLS and traffic visualization.

**Rationale**: Lightweight control plane (~200MB vs ~1GB for Istio), automatic sidecar injection, low latency overhead (~1ms per request).

---

## ADR-012: Horizontal + Vertical Scaling

**Context**: Need to scale services based on demand while optimizing resource utilization.

**Decision**: Implement HPA for scaling replicas and VPA for resource optimization.

**Configuration**:

- HPA scales services 1-3 replicas at 70% CPU/memory utilization
- VPA recommends optimal resource requests (mode: "Off" for safety)
- ResourceQuotas prevent runaway consumption
