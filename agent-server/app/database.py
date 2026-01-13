"""Database models and connection management."""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

from app.config import settings


# =============================================================================
# Database Engine
# =============================================================================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# =============================================================================
# Models
# =============================================================================

class Base(DeclarativeBase):
    pass


class APIKey(Base):
    """API key for authentication."""
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    key_prefix = Column(String(8), nullable=False)  # First 8 chars for identification
    scope = Column(String(20), nullable=False, default="agent-invoke")
    rate_limit = Column(Integer, default=100)  # Requests per minute
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    previous_key_id = Column(String(36), nullable=True)  # For rotation tracking
    metadata = Column(JSON, default={})
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="api_key")
    invocations = relationship("AgentInvocation", back_populates="api_key")


class AuditLog(Base):
    """Audit log for tracking all actions."""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    api_key_id = Column(String(36), ForeignKey("api_keys.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource = Column(String(100), nullable=False)
    details = Column(JSON, default={})
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Relationships
    api_key = relationship("APIKey", back_populates="audit_logs")


class AgentInvocation(Base):
    """Record of agent invocations."""
    __tablename__ = "agent_invocations"
    
    id = Column(String(36), primary_key=True)
    api_key_id = Column(String(36), ForeignKey("api_keys.id"), nullable=False, index=True)
    agent_type = Column(String(50), nullable=False, index=True)
    task_hash = Column(String(64), nullable=False)  # SHA256 of task for dedup
    model_used = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    priority = Column(String(10), default="normal")
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    api_key = relationship("APIKey", back_populates="invocations")


class Workflow(Base):
    """Stored workflow definitions."""
    __tablename__ = "workflows"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False)  # YAML/JSON workflow definition
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
