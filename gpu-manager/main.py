#!/usr/bin/env python3
"""
GPU Resource Manager - Dynamic GPU allocation for AI workloads.

This service manages GPU resources across multiple AI services (Ollama, ComfyUI, A1111)
implementing dynamic allocation based on active workloads.

Features:
- Full GPU allocation when only one service is active
- Smart splitting for concurrent pipelines/workflows
- Priority-based scheduling (inference > generation > transcription)
- Real-time monitoring via Prometheus metrics
- Automatic rebalancing based on queue depth

Architecture:
- Runs as a sidecar container on GPU worker
- Monitors nvidia-smi for utilization
- Adjusts CUDA_VISIBLE_DEVICES and memory limits dynamically
- Exposes REST API for coordination with orchestrator
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServiceType(str, Enum):
    OLLAMA = "ollama"
    COMFYUI = "comfyui"
    AUTOMATIC1111 = "automatic1111"
    WHISPER = "whisper"
    VIDEO_GEN = "video_gen"


class Priority(int, Enum):
    CRITICAL = 0  # System/health checks
    HIGH = 1      # Interactive inference
    NORMAL = 2    # Standard generation
    LOW = 3       # Background tasks
    BATCH = 4     # Bulk processing


@dataclass
class GPUInfo:
    """GPU hardware information."""
    index: int
    name: str
    total_memory_mb: int
    used_memory_mb: int
    free_memory_mb: int
    utilization_percent: int
    temperature_c: int
    power_draw_w: float
    processes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ServiceAllocation:
    """Resource allocation for a service."""
    service: ServiceType
    gpu_indices: List[int]
    memory_limit_mb: int
    priority: Priority
    active_requests: int = 0
    estimated_completion_s: float = 0.0
    last_activity: float = field(default_factory=time.time)


class AllocationRequest(BaseModel):
    service: ServiceType
    priority: Priority = Priority.NORMAL
    estimated_vram_mb: int = Field(default=4000, description="Estimated VRAM needed")
    estimated_duration_s: float = Field(default=30.0, description="Estimated task duration")
    workflow_type: Optional[str] = None
    pipeline_id: Optional[str] = None


class AllocationResponse(BaseModel):
    success: bool
    allocation_id: str
    gpu_indices: List[int]
    memory_limit_mb: int
    message: str
    wait_time_s: float = 0.0


class ReleaseRequest(BaseModel):
    allocation_id: str


class GPUResourceManager:
    """Manages dynamic GPU resource allocation."""
    
    # VRAM requirements by service (in MB)
    VRAM_REQUIREMENTS = {
        ServiceType.OLLAMA: {
            "min": 2000,   # Minimum for small models
            "default": 8000,  # Default for medium models
            "max": 24000,  # Large models (70B)
        },
        ServiceType.COMFYUI: {
            "min": 4000,   # SD 1.5
            "default": 10000,  # SDXL
            "max": 24000,  # Video generation
        },
        ServiceType.AUTOMATIC1111: {
            "min": 4000,
            "default": 8000,
            "max": 16000,
        },
        ServiceType.WHISPER: {
            "min": 1500,
            "default": 3000,
            "max": 6000,
        },
        ServiceType.VIDEO_GEN: {
            "min": 12000,
            "default": 20000,
            "max": 24000,
        },
    }
    
    # Service endpoints for health checks
    SERVICE_ENDPOINTS = {
        ServiceType.OLLAMA: "http://localhost:11434/api/tags",
        ServiceType.COMFYUI: "http://localhost:8188/system_stats",
        ServiceType.AUTOMATIC1111: "http://localhost:7860/sdapi/v1/progress",
        ServiceType.WHISPER: "http://localhost:9000/health",
    }
    
    def __init__(self):
        self.gpus: List[GPUInfo] = []
        self.allocations: Dict[str, ServiceAllocation] = {}
        self.allocation_counter = 0
        self.lock = asyncio.Lock()
        self.total_vram_mb = 0
        self._monitoring_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize GPU manager and start monitoring."""
        await self.refresh_gpu_info()
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"GPU Manager initialized with {len(self.gpus)} GPUs, "
                   f"total VRAM: {self.total_vram_mb}MB")
        
    async def shutdown(self):
        """Clean shutdown."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
                
    async def refresh_gpu_info(self) -> List[GPUInfo]:
        """Query nvidia-smi for GPU information."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,memory.total,memory.used,memory.free,"
                    "utilization.gpu,temperature.gpu,power.draw",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"nvidia-smi failed: {result.stderr}")
                return self.gpus
                
            self.gpus = []
            self.total_vram_mb = 0
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 8:
                    gpu = GPUInfo(
                        index=int(parts[0]),
                        name=parts[1],
                        total_memory_mb=int(float(parts[2])),
                        used_memory_mb=int(float(parts[3])),
                        free_memory_mb=int(float(parts[4])),
                        utilization_percent=int(float(parts[5])),
                        temperature_c=int(float(parts[6])),
                        power_draw_w=float(parts[7]) if parts[7] != '[N/A]' else 0.0,
                    )
                    self.gpus.append(gpu)
                    self.total_vram_mb += gpu.total_memory_mb
                    
            # Get process info
            proc_result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-compute-apps=pid,gpu_uuid,used_memory,process_name",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc_result.returncode == 0:
                for line in proc_result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 4:
                        # Match to GPU (simplified - assumes single GPU)
                        if self.gpus:
                            self.gpus[0].processes.append({
                                "pid": int(parts[0]),
                                "memory_mb": int(float(parts[2])) if parts[2] else 0,
                                "name": parts[3]
                            })
                            
        except Exception as e:
            logger.error(f"Error refreshing GPU info: {e}")
            
        return self.gpus
        
    async def _monitor_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(5)
                await self.refresh_gpu_info()
                await self._cleanup_stale_allocations()
                await self._rebalance_if_needed()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                
    async def _cleanup_stale_allocations(self):
        """Remove allocations that haven't been active for a while."""
        now = time.time()
        stale_timeout = 300  # 5 minutes
        
        async with self.lock:
            stale = [
                aid for aid, alloc in self.allocations.items()
                if (now - alloc.last_activity) > stale_timeout and alloc.active_requests == 0
            ]
            for aid in stale:
                logger.info(f"Cleaning up stale allocation: {aid}")
                del self.allocations[aid]
                
    async def _rebalance_if_needed(self):
        """Rebalance GPU resources based on current workloads."""
        if not self.gpus:
            return
            
        async with self.lock:
            active_services = [
                alloc for alloc in self.allocations.values()
                if alloc.active_requests > 0
            ]
            
            if len(active_services) == 0:
                # No active services - nothing to do
                return
            elif len(active_services) == 1:
                # Single active service gets full GPU
                alloc = active_services[0]
                alloc.memory_limit_mb = self.total_vram_mb
                alloc.gpu_indices = list(range(len(self.gpus)))
            else:
                # Multiple services - split based on priority and requirements
                await self._split_resources(active_services)
                
    async def _split_resources(self, services: List[ServiceAllocation]):
        """Split GPU resources among multiple services."""
        # Sort by priority (lower = higher priority)
        services.sort(key=lambda s: (s.priority, -s.active_requests))
        
        available_vram = self.total_vram_mb
        allocated = {}
        
        for service in services:
            reqs = self.VRAM_REQUIREMENTS.get(service.service, {"min": 2000, "default": 4000})
            min_vram = reqs["min"]
            default_vram = reqs["default"]
            
            if service.priority == Priority.CRITICAL:
                # Critical gets what it needs
                alloc_vram = min(default_vram, available_vram)
            elif service.priority == Priority.HIGH:
                # High priority gets 60% of remaining
                alloc_vram = min(int(available_vram * 0.6), default_vram)
            else:
                # Others split remaining equally
                remaining_services = len(services) - len(allocated)
                alloc_vram = min(available_vram // max(remaining_services, 1), default_vram)
                
            # Ensure minimum
            alloc_vram = max(min_vram, alloc_vram)
            
            service.memory_limit_mb = alloc_vram
            allocated[service.service] = alloc_vram
            available_vram -= alloc_vram
            
        logger.info(f"Rebalanced allocations: {allocated}")
        
    async def check_service_health(self, service: ServiceType) -> bool:
        """Check if a service is healthy."""
        endpoint = self.SERVICE_ENDPOINTS.get(service)
        if not endpoint:
            return True
            
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(endpoint, timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
            
    async def request_allocation(self, request: AllocationRequest) -> AllocationResponse:
        """Request GPU resources for a task."""
        async with self.lock:
            self.allocation_counter += 1
            allocation_id = f"alloc-{request.service.value}-{self.allocation_counter}"
            
            # Check if we have enough VRAM
            await self.refresh_gpu_info()
            
            if not self.gpus:
                raise HTTPException(status_code=503, detail="No GPUs available")
                
            available_vram = self.gpus[0].free_memory_mb
            
            # Check existing allocations
            active_allocations = sum(
                1 for a in self.allocations.values() if a.active_requests > 0
            )
            
            wait_time = 0.0
            
            if request.estimated_vram_mb > available_vram:
                if active_allocations > 0:
                    # Need to wait for other services
                    avg_completion = sum(
                        a.estimated_completion_s 
                        for a in self.allocations.values() 
                        if a.active_requests > 0
                    ) / max(active_allocations, 1)
                    wait_time = avg_completion
                else:
                    # Not enough VRAM even when idle
                    pass
                    
            # Determine allocation size
            reqs = self.VRAM_REQUIREMENTS.get(request.service, {"default": 4000})
            
            if active_allocations == 0:
                # Full GPU available
                memory_limit = self.total_vram_mb
            else:
                # Split resources
                memory_limit = min(
                    request.estimated_vram_mb,
                    available_vram,
                    reqs.get("max", self.total_vram_mb)
                )
                
            allocation = ServiceAllocation(
                service=request.service,
                gpu_indices=[0],  # Single GPU for now
                memory_limit_mb=memory_limit,
                priority=request.priority,
                active_requests=1,
                estimated_completion_s=request.estimated_duration_s,
            )
            
            self.allocations[allocation_id] = allocation
            
            logger.info(
                f"Allocated {memory_limit}MB to {request.service.value} "
                f"(id={allocation_id}, priority={request.priority.name})"
            )
            
            return AllocationResponse(
                success=True,
                allocation_id=allocation_id,
                gpu_indices=allocation.gpu_indices,
                memory_limit_mb=allocation.memory_limit_mb,
                message=f"Allocated {memory_limit}MB VRAM",
                wait_time_s=wait_time,
            )
            
    async def release_allocation(self, allocation_id: str):
        """Release GPU resources."""
        async with self.lock:
            if allocation_id in self.allocations:
                alloc = self.allocations[allocation_id]
                alloc.active_requests = max(0, alloc.active_requests - 1)
                alloc.last_activity = time.time()
                logger.info(f"Released allocation: {allocation_id}")
            else:
                logger.warning(f"Unknown allocation: {allocation_id}")
                
    def get_status(self) -> Dict[str, Any]:
        """Get current GPU status."""
        return {
            "gpus": [
                {
                    "index": gpu.index,
                    "name": gpu.name,
                    "total_memory_mb": gpu.total_memory_mb,
                    "used_memory_mb": gpu.used_memory_mb,
                    "free_memory_mb": gpu.free_memory_mb,
                    "utilization_percent": gpu.utilization_percent,
                    "temperature_c": gpu.temperature_c,
                    "power_draw_w": gpu.power_draw_w,
                }
                for gpu in self.gpus
            ],
            "allocations": {
                aid: {
                    "service": alloc.service.value,
                    "memory_limit_mb": alloc.memory_limit_mb,
                    "priority": alloc.priority.name,
                    "active_requests": alloc.active_requests,
                }
                for aid, alloc in self.allocations.items()
            },
            "total_vram_mb": self.total_vram_mb,
        }


# FastAPI application
gpu_manager = GPUResourceManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    await gpu_manager.initialize()
    yield
    await gpu_manager.shutdown()


app = FastAPI(
    title="GPU Resource Manager",
    description="Dynamic GPU allocation for AI workloads",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "gpus": len(gpu_manager.gpus)}


@app.get("/status")
async def status():
    """Get GPU and allocation status."""
    return gpu_manager.get_status()


@app.post("/allocate", response_model=AllocationResponse)
async def allocate(request: AllocationRequest):
    """Request GPU allocation."""
    return await gpu_manager.request_allocation(request)


@app.post("/release")
async def release(request: ReleaseRequest):
    """Release GPU allocation."""
    await gpu_manager.release_allocation(request.allocation_id)
    return {"success": True, "message": f"Released {request.allocation_id}"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    status = gpu_manager.get_status()
    lines = []
    
    # GPU metrics
    for gpu in status["gpus"]:
        idx = gpu["index"]
        lines.append(f'gpu_memory_total_mb{{gpu="{idx}"}} {gpu["total_memory_mb"]}')
        lines.append(f'gpu_memory_used_mb{{gpu="{idx}"}} {gpu["used_memory_mb"]}')
        lines.append(f'gpu_memory_free_mb{{gpu="{idx}"}} {gpu["free_memory_mb"]}')
        lines.append(f'gpu_utilization_percent{{gpu="{idx}"}} {gpu["utilization_percent"]}')
        lines.append(f'gpu_temperature_celsius{{gpu="{idx}"}} {gpu["temperature_c"]}')
        lines.append(f'gpu_power_watts{{gpu="{idx}"}} {gpu["power_draw_w"]}')
        
    # Allocation metrics
    active = sum(1 for a in status["allocations"].values() if a["active_requests"] > 0)
    lines.append(f'gpu_active_allocations {active}')
    lines.append(f'gpu_total_allocations {len(status["allocations"])}')
    
    return "\n".join(lines)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
