---
title: Troubleshooting
description: Common issues and their solutions
---

# Troubleshooting

## Pod CrashLoopBackOff

```bash
# Check logs for errors
kubectl logs deployment/<name> -n <namespace> --previous

# Check events
kubectl describe pod -l app=<name> -n <namespace>
```

**Common fixes**:

- **Memory limits**: Increase in `values.yaml`
- **Config errors**: Check ConfigMaps/Secrets
- **Dependency**: Check dependent services are running

## Certificate Issues

```bash
# Check certificate status
kubectl get certificates -n cert-manager -o wide

# Check challenges
kubectl get challenges -n cert-manager

# Force certificate renewal
kubectl delete certificate <name> -n cert-manager
# ArgoCD will recreate it
```

## DNS Resolution

```bash
# Test from inside cluster
kubectl run -it --rm debug --image=busybox -- nslookup ai.vectorweight.com

# Check CoreDNS
kubectl logs -n kube-system -l k8s-app=kube-dns

# Restart CoreDNS
kubectl rollout restart deployment/coredns -n kube-system
```

## Ingress/Traefik

```bash
# Check Traefik logs
kubectl logs -n traefik -l app.kubernetes.io/name=traefik

# Verify IngressRoutes
kubectl get ingressroute -A

# Test connectivity
curl -k https://ai.vectorweight.com/health
```

## High Memory Usage

```bash
# Check resource usage
kubectl top pods -A --sort-by=memory

# Check Ollama model memory
curl http://192.168.1.99:11434/api/ps | jq

# Unload unused models
curl -X POST http://192.168.1.99:11434/api/generate \
  -d '{"model":"unused-model","keep_alive":0}'
```

## Slow Inference

```bash
# Check GPU utilization (on GPU worker)
nvidia-smi

# Check LiteLLM queue
curl -s https://llm.vectorweight.com/queue/status

# Check rate limits
kubectl logs deployment/litellm -n self-hosted-ai | grep rate
```

## Tracing Issues

### No Traces Appearing

```bash
# Check OTel Collector is running
kubectl get pods -n monitoring -l app.kubernetes.io/name=opentelemetry-collector

# Check collector logs
kubectl logs -n monitoring -l app.kubernetes.io/name=opentelemetry-collector -f

# Verify service has OTEL env vars
kubectl get deployment litellm -n ai-services -o yaml | grep OTEL
```

### Traces Incomplete

```bash
# Check trace sampling rate
kubectl get configmap -n monitoring otel-collector-config -o yaml | grep sampling

# Check for dropped spans
kubectl logs -n monitoring -l app.kubernetes.io/name=opentelemetry-collector | grep dropped
```

## Emergency Procedures

### Full Cluster Recovery

```bash
# 1. Verify node connectivity
kubectl get nodes

# 2. Check ArgoCD
kubectl get pods -n argocd
argocd app sync --prune root

# 3. Verify critical services
kubectl get pods -n self-hosted-ai
kubectl get pods -n monitoring

# 4. Test endpoints
curl -k https://ai.vectorweight.com/health
```

### Database Recovery

```bash
# 1. Stop dependent services
kubectl scale deployment litellm --replicas=0 -n self-hosted-ai

# 2. Restore from backup
uv run scripts/backup.py restore 20260115_120000 --component postgresql

# 3. Restart services
kubectl scale deployment litellm --replicas=1 -n self-hosted-ai
```

### Secret Recovery

```bash
# If SealedSecrets key is lost, regenerate all secrets:

# 1. Backup current secrets (if accessible)
kubectl get secrets -A -o yaml > secrets-backup.yaml

# 2. Reinstall SealedSecrets
kubectl delete -n kube-system deploy sealed-secrets-controller
argocd app sync sealed-secrets

# 3. Regenerate and apply secrets
uv run scripts/secrets_manager.py generate

# 4. Restart all deployments
kubectl rollout restart deployment -A
```
