# Self-Hosted AI Helm Charts

This directory contains Helm charts for deploying the Self-Hosted AI stack to Kubernetes using ArgoCD.

## Charts

### server
Deploys the server components:
- Open WebUI
- Ollama CPU
- Redis
- Monitoring stack (Prometheus, Grafana, Loki, Promtail, Node Exporter)

### gpu-worker
Deploys the GPU worker components:
- Ollama GPU
- ComfyUI

## Deployment

### Prerequisites

1. Kubernetes cluster with ArgoCD installed
2. Storage classes configured (local-path, nfs-client, ceph-rbd)
3. GPU nodes labeled with `gpu: "true"` for GPU workloads
4. NVIDIA GPU Operator installed for GPU support

### Using Helmfile

```bash
# Install Helmfile
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh

# Install Helmfile
wget https://github.com/helmfile/helmfile/releases/latest/download/helmfile_$(uname -s)_$(uname -m).tar.gz
tar -xzf helmfile_*.tar.gz
sudo mv helmfile /usr/local/bin/

# Deploy to dev environment
cd helmfile
helmfile --environment dev sync

# Deploy to prod
helmfile --environment prod sync
```

### Using ArgoCD

1. Apply the Application manifests:
```bash
kubectl apply -f argocd/server-application.yaml
kubectl apply -f argocd/gpu-worker-application.yaml
```

2. ArgoCD will automatically sync the applications from the GitHub repository.

## Configuration

### Environment Variables

Create secrets for sensitive data:

```bash
kubectl create secret generic webui-secret \
  --from-literal=secret-key="$(openssl rand -hex 32)" \
  --namespace self-hosted-ai
```

### Storage

Configure storage classes in `values.yaml` or via Helm parameters:

- `local-path`: For local development
- `nfs-client`: For shared NFS storage
- `ceph-rbd`: For production Ceph storage

### GPU Support

Ensure GPU nodes are properly labeled and tainted:

```bash
kubectl label nodes <gpu-node> gpu=true
kubectl taint nodes <gpu-node> nvidia.com/gpu=:NoSchedule
```

## Monitoring

The monitoring stack includes:

- **Prometheus**: Metrics collection
- **Grafana**: Dashboards (default login: admin/admin)
- **Loki**: Log aggregation
- **Promtail**: Log shipping
- **Node Exporter**: Node metrics
- **Alerting**: Pre-configured alerts for service health

Access Grafana at: `http://grafana.self-hosted-ai.svc.cluster.local`

## Scaling

Adjust replica counts and resource limits in `values.yaml`:

```yaml
openwebui:
  replicaCount: 2
  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
```

## Troubleshooting

### Check ArgoCD sync status
```bash
kubectl get applications -n argocd
kubectl describe application self-hosted-ai-server -n argocd
```

### View logs
```bash
kubectl logs -n self-hosted-ai deployment/self-hosted-ai-server-openwebui
```

### Debug Helm releases
```bash
helm list -n self-hosted-ai
helm status self-hosted-ai-server -n self-hosted-ai
```