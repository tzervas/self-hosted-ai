# GPU Workload Testing Results

**Date**: 2026-02-07
**Branch**: `fix/gpu-workload-enablement`
**Phase**: 1.1 - GPU Workload Enablement

## Summary

Tested GPU workload functionality on akula-prime node (RTX 5080 16GB). All GPU services can successfully utilize the GPU, but **only one workload can run at a time** due to single GPU constraint.

## Test Results

### ✅ Working GPU Workloads

| Service | Status | GPU Test | Notes |
|---------|--------|----------|-------|
| **ollama-gpu** | ✅ Running | `nvidia-smi` confirmed RTX 5080 | Primary LLM inference service |
| **audio-server** | ✅ Running | No GPU request | CPU-only, runs alongside GPU workloads |
| **tts-server** | ✅ Running | No GPU request | CPU-only, runs alongside GPU workloads |
| **video-server** | ✅ Running | No GPU request | CPU-only, runs alongside GPU workloads |
| **ComfyUI** | 🔄 Tested | Scheduled successfully when GPU available | Image generation service |

### GPU Allocation

- **Node**: akula-prime (192.168.1.99)
- **GPU**: NVIDIA GeForce RTX 5080, 16303 MiB
- **Driver**: 590.48.01
- **CUDA**: 13.1
- **Allocatable**: `nvidia.com/gpu: 1` (single GPU)

### GPU Operator Status

| Component | Status | Notes |
|-----------|--------|-------|
| **nvidia-device-plugin** | ✅ 2/2 Running | Main plugin working, config-manager functional |
| **gpu-feature-discovery** | ✅ 2/2 Running | GPU labels applied correctly |
| **GPU labels** | ✅ Applied | All nvidia.com/gpu.* labels present |

## Issues Identified

### 1. Single GPU Constraint

**Problem**: akula-prime has only 1 physical GPU, but multiple services request full GPU allocation:
- `ollama-gpu`: requests `nvidia.com/gpu: 1`
- `comfyui`: requests `nvidia.com/gpu: 1`
- `automatic1111`: requests `nvidia.com/gpu: 1`

**Impact**: Only one GPU workload can run at a time. When ollama-gpu is running, ComfyUI and Automatic1111 remain in **Pending** state.

**Solution Options**:

1. **GPU Time-Slicing** (recommended for production)
   - Enable NVIDIA device plugin time-slicing
   - ConfigMap exists: `time-slicing-config` in `gpu-operator` namespace
   - Needs proper configuration with `replicas: 4` to virtualize 1 GPU → 4 GPUs
   - **Status**: Attempted but ConfigMap format issues - needs more research

2. **Fractional GPU Requests** (interim solution)
   - Change ollama-gpu to `nvidia.com/gpu: 0.5`
   - Change comfyui to `nvidia.com/gpu: 0.5`
   - Requires time-slicing enabled first

3. **Disable Non-Critical GPU Workloads** (current solution)
   - Keep ollama-gpu enabled (primary LLM service)
   - Disable ComfyUI and Automatic1111 until time-slicing configured
   - **Status**: Implemented in `helm/gpu-worker/values.yaml`

4. **Add More GPUs** (hardware solution)
   - Install additional GPU in akula-prime
   - Most expensive but eliminates scheduling conflicts

### 2. ArgoCD Auto-Sync Interference

**Problem**: Manual `kubectl scale` commands are reverted by ArgoCD auto-sync.

**Solution**: All deployment changes must be made in Helm charts (`helm/gpu-worker/values.yaml`), not directly via kubectl.

## Configuration Changes

### helm/gpu-worker/values.yaml

```yaml
# ComfyUI - Disabled due to single GPU constraint
comfyui:
  enabled: false  # Changed from true

# Automatic1111 - Disabled due to single GPU constraint
automatic1111:
  enabled: false  # Changed from true
```

Added notes explaining the single GPU constraint and requirement for time-slicing.

## Next Steps

### Short-Term (Complete Phase 1.1)

1. ✅ Verify ollama-gpu is stable and using GPU
2. ✅ Document GPU allocation constraints
3. ✅ Disable conflicting GPU workloads
4. ⏭️ Commit changes to feature branch
5. ⏭️ Test ArgoCD sync with updated values

### Medium-Term (Phase 2 or 3)

1. Research correct NVIDIA device plugin time-slicing configuration format
2. Create proper `time-slicing-config` ConfigMap
3. Test GPU virtualization (1 physical → 4 virtual GPUs)
4. Re-enable ComfyUI and Automatic1111
5. Document time-slicing setup in OPERATIONS.md

### Long-Term (Future Phases)

1. Consider adding second GPU to akula-prime for dedicated image generation
2. Or dedicate separate node for image generation workloads
3. Implement GPU resource quotas and priorities

## Verification Commands

```bash
# Check GPU allocation
kubectl get node akula-prime -o json | jq '.status.allocatable["nvidia.com/gpu"]'

# Test GPU in running pod
kubectl exec -n gpu-workloads ollama-gpu-<pod-id> -- nvidia-smi

# Check GPU operator status
kubectl get pods -n gpu-operator | grep -E '(nvidia-device-plugin|gpu-feature-discovery)'

# View GPU labels
kubectl get node akula-prime -o json | jq '.metadata.labels | to_entries | .[] | select(.key | contains("nvidia"))'
```

## References

- [NVIDIA Device Plugin Documentation](https://github.com/NVIDIA/k8s-device-plugin)
- [GPU Time-Slicing Guide](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)
- Phase 1.1 tasks in `docs/DEVELOPMENT_ROADMAP.md`

---

**Status**: GPU functionality verified ✅ Single GPU constraint documented ✅ Non-critical workloads disabled ✅
