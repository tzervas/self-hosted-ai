"""Agent Server - FastAPI Application

Dedicated server for running AI agents with:
- Google ADK orchestration
- Secure API key authentication with 90-day rotation
- Priority-based request queuing
- Comprehensive audit logging
- Prometheus metrics
"""

import asyncio
import hashlib
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field
from starlette.responses import Response
import httpx
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, init_db
from app.models import APIKey, AuditLog, AgentInvocation
from app.auth import verify_api_key, get_current_key


# =============================================================================
# Prometheus Metrics
# =============================================================================

REQUEST_COUNT = Counter(
    "agent_server_requests_total",
    "Total requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "agent_server_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"]
)
AGENT_INVOCATIONS = Counter(
    "agent_server_invocations_total",
    "Total agent invocations",
    ["agent_type", "status"]
)
AGENT_DURATION = Histogram(
    "agent_server_agent_duration_seconds",
    "Agent execution duration",
    ["agent_type"]
)
ACTIVE_AGENTS = Gauge(
    "agent_server_active_agents",
    "Currently running agents"
)
API_KEY_AGE_DAYS = Gauge(
    "agent_server_api_key_age_days",
    "Age of API keys in days",
    ["key_id", "scope"]
)


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    await init_db()
    app.state.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.http_client = httpx.AsyncClient(timeout=settings.DEFAULT_TIMEOUT)
    
    # Background task for key rotation warnings
    asyncio.create_task(key_rotation_monitor())
    
    yield
    
    # Shutdown
    await app.state.redis.close()
    await app.state.http_client.aclose()


app = FastAPI(
    title="Self-Hosted AI Agent Server",
    description="Production-grade agent orchestration with Google ADK",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request Models
# =============================================================================

class AgentInvokeRequest(BaseModel):
    """Request to invoke an agent."""
    agent_type: str = Field(..., description="Agent type: development, code_review, testing, documentation, research")
    task: str = Field(..., description="Task description or prompt")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    model: Optional[str] = Field(default=None, description="Override default model")
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    priority: Optional[str] = Field(default="normal", pattern="^(high|normal|low)$")
    timeout: Optional[int] = Field(default=None, ge=30, le=3600)
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_type": "development",
                "task": "Implement a REST API endpoint for user authentication",
                "context": {"language": "python", "framework": "fastapi"},
                "priority": "high"
            }
        }


class WorkflowRequest(BaseModel):
    """Request to execute a multi-agent workflow."""
    workflow_name: str = Field(..., description="Workflow name")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Workflow inputs")
    priority: Optional[str] = Field(default="normal")


class APIKeyCreateRequest(BaseModel):
    """Request to create an API key."""
    name: str = Field(..., min_length=1, max_length=100)
    scope: str = Field(default="agent-invoke", pattern="^(admin|agent-invoke|read-only)$")
    rate_limit: Optional[int] = Field(default=100, ge=1, le=10000, description="Requests per minute")
    expires_days: Optional[int] = Field(default=90, ge=1, le=365)


class AgentResponse(BaseModel):
    """Agent execution response."""
    invocation_id: str
    status: str
    agent_type: str
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    model_used: str
    tokens_used: Optional[Dict[str, int]] = None


# =============================================================================
# Health & Metrics Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health/readiness")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check - verifies database and Redis connectivity."""
    checks = {"database": False, "redis": False, "litellm": False}
    
    try:
        await db.execute(select(1))
        checks["database"] = True
    except Exception:
        pass
    
    try:
        await app.state.redis.ping()
        checks["redis"] = True
    except Exception:
        pass
    
    try:
        response = await app.state.http_client.get(f"{settings.LITELLM_URL}/health")
        checks["litellm"] = response.status_code == 200
    except Exception:
        pass
    
    all_healthy = all(checks.values())
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# =============================================================================
# Agent Endpoints
# =============================================================================

@app.post("/v1/agents/invoke", response_model=AgentResponse)
async def invoke_agent(
    request: AgentInvokeRequest,
    api_key: APIKey = Depends(get_current_key),
    db: AsyncSession = Depends(get_db)
):
    """Invoke a single agent with the specified task."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Validate scope
    if api_key.scope == "read-only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only keys cannot invoke agents"
        )
    
    # Check rate limit
    rate_key = f"rate:{api_key.id}:{int(time.time()) // 60}"
    current_rate = await app.state.redis.incr(rate_key)
    await app.state.redis.expire(rate_key, 60)
    
    if current_rate > api_key.rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    ACTIVE_AGENTS.inc()
    
    try:
        # Import ADK agent wrapper
        from app.adk_agents import invoke_adk_agent
        
        result = await invoke_adk_agent(
            agent_type=request.agent_type,
            task=request.task,
            context=request.context,
            model=request.model or settings.DEFAULT_MODEL,
            temperature=request.temperature or settings.DEFAULT_TEMPERATURE,
            timeout=request.timeout or settings.DEFAULT_TIMEOUT,
            priority=request.priority,
            http_client=app.state.http_client,
            litellm_url=settings.LITELLM_URL,
            litellm_key=settings.LITELLM_API_KEY
        )
        
        duration = time.time() - start_time
        
        # Record metrics
        AGENT_INVOCATIONS.labels(agent_type=request.agent_type, status="success").inc()
        AGENT_DURATION.labels(agent_type=request.agent_type).observe(duration)
        
        # Audit log
        await create_audit_log(
            db=db,
            api_key_id=api_key.id,
            action="agent_invoke",
            resource=request.agent_type,
            details={
                "invocation_id": invocation_id,
                "task_preview": request.task[:100],
                "model": result.get("model_used"),
                "duration": duration
            }
        )
        
        return AgentResponse(
            invocation_id=invocation_id,
            status="completed",
            agent_type=request.agent_type,
            output=result.get("output"),
            duration_seconds=duration,
            model_used=result.get("model_used", settings.DEFAULT_MODEL),
            tokens_used=result.get("tokens")
        )
        
    except Exception as e:
        duration = time.time() - start_time
        AGENT_INVOCATIONS.labels(agent_type=request.agent_type, status="error").inc()
        
        await create_audit_log(
            db=db,
            api_key_id=api_key.id,
            action="agent_invoke_error",
            resource=request.agent_type,
            details={"invocation_id": invocation_id, "error": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        ACTIVE_AGENTS.dec()


@app.post("/v1/workflows/execute")
async def execute_workflow(
    request: WorkflowRequest,
    api_key: APIKey = Depends(get_current_key),
    db: AsyncSession = Depends(get_db)
):
    """Execute a multi-agent workflow."""
    if api_key.scope == "read-only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only keys cannot execute workflows"
        )
    
    from app.adk_agents import execute_adk_workflow
    
    workflow_id = str(uuid.uuid4())
    
    await create_audit_log(
        db=db,
        api_key_id=api_key.id,
        action="workflow_execute",
        resource=request.workflow_name,
        details={"workflow_id": workflow_id, "inputs": list(request.inputs.keys())}
    )
    
    result = await execute_adk_workflow(
        workflow_name=request.workflow_name,
        inputs=request.inputs,
        priority=request.priority,
        http_client=app.state.http_client,
        litellm_url=settings.LITELLM_URL,
        litellm_key=settings.LITELLM_API_KEY
    )
    
    return {
        "workflow_id": workflow_id,
        "status": result.get("status"),
        "outputs": result.get("outputs"),
        "duration_seconds": result.get("duration")
    }


@app.get("/v1/agents/types")
async def list_agent_types(api_key: APIKey = Depends(get_current_key)):
    """List available agent types."""
    return {
        "agents": [
            {
                "type": "development",
                "description": "Code generation, implementation, and refactoring",
                "capabilities": ["code_generation", "refactoring", "implementation"]
            },
            {
                "type": "code_review",
                "description": "Code quality review, security analysis, and scoring",
                "capabilities": ["review", "security_analysis", "scoring"]
            },
            {
                "type": "testing",
                "description": "Test generation, edge cases, and coverage analysis",
                "capabilities": ["test_generation", "edge_cases", "coverage"]
            },
            {
                "type": "documentation",
                "description": "API docs, guides, and README generation",
                "capabilities": ["api_docs", "guides", "readme"]
            },
            {
                "type": "research",
                "description": "Information gathering, synthesis, and reports",
                "capabilities": ["research", "synthesis", "reports"]
            }
        ]
    }


# =============================================================================
# API Key Management
# =============================================================================

@app.post("/v1/keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreateRequest,
    api_key: APIKey = Depends(get_current_key),
    db: AsyncSession = Depends(get_db)
):
    """Create a new API key (admin only)."""
    if api_key.scope != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin keys can create new keys"
        )
    
    # Generate secure key
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    new_key = APIKey(
        id=str(uuid.uuid4()),
        name=request.name,
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        scope=request.scope,
        rate_limit=request.rate_limit,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=request.expires_days),
        is_active=True
    )
    
    db.add(new_key)
    await db.commit()
    
    await create_audit_log(
        db=db,
        api_key_id=api_key.id,
        action="key_create",
        resource=new_key.id,
        details={"name": request.name, "scope": request.scope}
    )
    
    return {
        "id": new_key.id,
        "name": new_key.name,
        "key": raw_key,  # Only returned once
        "scope": new_key.scope,
        "rate_limit": new_key.rate_limit,
        "expires_at": new_key.expires_at.isoformat(),
        "warning": "Save this key securely. It will not be shown again."
    }


@app.get("/v1/keys")
async def list_api_keys(
    api_key: APIKey = Depends(get_current_key),
    db: AsyncSession = Depends(get_db)
):
    """List all API keys (admin only, key values hidden)."""
    if api_key.scope != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin keys can list keys"
        )
    
    result = await db.execute(select(APIKey).where(APIKey.is_active == True))
    keys = result.scalars().all()
    
    return {
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scope": k.scope,
                "rate_limit": k.rate_limit,
                "created_at": k.created_at.isoformat(),
                "expires_at": k.expires_at.isoformat(),
                "age_days": (datetime.now(timezone.utc) - k.created_at).days,
                "days_until_expiry": (k.expires_at - datetime.now(timezone.utc)).days
            }
            for k in keys
        ]
    }


@app.delete("/v1/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    api_key: APIKey = Depends(get_current_key),
    db: AsyncSession = Depends(get_db)
):
    """Revoke an API key (admin only)."""
    if api_key.scope != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin keys can revoke keys"
        )
    
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    target_key = result.scalar_one_or_none()
    
    if not target_key:
        raise HTTPException(status_code=404, detail="Key not found")
    
    target_key.is_active = False
    target_key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    
    await create_audit_log(
        db=db,
        api_key_id=api_key.id,
        action="key_revoke",
        resource=key_id,
        details={"name": target_key.name}
    )
    
    return {"status": "revoked", "key_id": key_id}


@app.post("/v1/keys/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    api_key: APIKey = Depends(get_current_key),
    db: AsyncSession = Depends(get_db)
):
    """Rotate an API key, returning new key with 7-day grace period for old key."""
    if api_key.scope != "admin" and api_key.id != key_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only rotate own key or admin required"
        )
    
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    old_key = result.scalar_one_or_none()
    
    if not old_key:
        raise HTTPException(status_code=404, detail="Key not found")
    
    # Generate new key
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    new_key = APIKey(
        id=str(uuid.uuid4()),
        name=f"{old_key.name} (rotated)",
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        scope=old_key.scope,
        rate_limit=old_key.rate_limit,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.API_KEY_ROTATION_DAYS),
        is_active=True,
        previous_key_id=old_key.id
    )
    
    # Set grace period for old key
    old_key.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    db.add(new_key)
    await db.commit()
    
    await create_audit_log(
        db=db,
        api_key_id=api_key.id,
        action="key_rotate",
        resource=key_id,
        details={"new_key_id": new_key.id, "grace_period_days": 7}
    )
    
    return {
        "new_key": {
            "id": new_key.id,
            "key": raw_key,
            "expires_at": new_key.expires_at.isoformat()
        },
        "old_key": {
            "id": old_key.id,
            "grace_period_expires": old_key.expires_at.isoformat()
        },
        "warning": "Save this key securely. Old key valid for 7 more days."
    }


# =============================================================================
# Audit & Utilities
# =============================================================================

async def create_audit_log(
    db: AsyncSession,
    api_key_id: str,
    action: str,
    resource: str,
    details: Dict[str, Any]
):
    """Create an audit log entry."""
    if not settings.AUDIT_LOG_ENABLED:
        return
    
    log = AuditLog(
        id=str(uuid.uuid4()),
        api_key_id=api_key_id,
        action=action,
        resource=resource,
        details=details,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)
    await db.commit()


async def key_rotation_monitor():
    """Background task to monitor key expiration and emit warnings."""
    while True:
        try:
            from app.database import async_session_maker
            async with async_session_maker() as db:
                result = await db.execute(
                    select(APIKey).where(APIKey.is_active == True)
                )
                keys = result.scalars().all()
                
                for key in keys:
                    age_days = (datetime.now(timezone.utc) - key.created_at).days
                    API_KEY_AGE_DAYS.labels(key_id=key.id, scope=key.scope).set(age_days)
                    
                    # Check if warning threshold reached
                    days_until_expiry = (key.expires_at - datetime.now(timezone.utc)).days
                    if days_until_expiry <= settings.API_KEY_WARNING_DAYS - settings.API_KEY_ROTATION_DAYS + 10:
                        # Log warning (could also send alerts here)
                        print(f"WARNING: API key {key.name} ({key.key_prefix}...) expires in {days_until_expiry} days")
        except Exception as e:
            print(f"Key rotation monitor error: {e}")
        
        await asyncio.sleep(3600)  # Check hourly


@app.get("/v1/audit")
async def get_audit_logs(
    limit: int = 100,
    api_key: APIKey = Depends(get_current_key),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs (admin only)."""
    if api_key.scope != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    )
    logs = result.scalars().all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "api_key_id": log.api_key_id,
                "action": log.action,
                "resource": log.resource,
                "details": log.details,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]
    }
