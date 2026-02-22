---
title: Development Roadmap
description: Planned features and development phases
---

# Development Roadmap

## Completed

- [x] Kubernetes (k3s) migration from Docker Compose
- [x] ArgoCD GitOps with App-of-Apps pattern
- [x] Keycloak SSO integration with oauth2-proxy
- [x] GitLab deployment with external PostgreSQL/Redis
- [x] Claude Code agents and automation hooks
- [x] Multimodal AI services (audio, video, TTS)
- [x] Comprehensive documentation system
- [x] Linkerd service mesh
- [x] HPA/VPA autoscaling
- [x] GitHub Actions runners (ARC)
- [x] Security hardening (PSS, NetworkPolicy)

## Planned

- [ ] Multi-node cluster support
- [ ] External secret store (Vault)
- [ ] Advanced RBAC per service
- [ ] Automated security scanning in CI
- [ ] PVC resize automation
- [ ] Complete TLS validation fix (2 services remaining)
- [ ] Single-node portable k3s solution (separate repo)

## Technology Watch

- **MCP Evolution**: Monitor protocol updates and tooling
- **Ollama**: Track new model support and quantization
- **k3s**: Evaluate upgrade path and new releases
- **ArgoCD**: Evaluate ApplicationSets for multi-env support
- **Linkerd**: Monitor for stability updates
