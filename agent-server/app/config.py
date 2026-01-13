"""Agent Server Configuration"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://agent:agent@localhost:5432/agent_server"
    REDIS_URL: str = "redis://localhost:6379/1"
    
    # API Security
    API_SECRET_KEY: str = "change-me-in-production"
    API_KEY_ROTATION_DAYS: int = 90
    API_KEY_WARNING_DAYS: int = 80
    
    # LiteLLM Backend
    LITELLM_URL: str = "http://localhost:4000"
    LITELLM_API_KEY: str = ""
    
    # Ollama Direct (fallback)
    OLLAMA_GPU_URL: str = "http://192.168.1.99:11434"
    OLLAMA_CPU_URL: str = "http://localhost:11434"
    
    # Agent Configuration
    DEFAULT_MODEL: str = "qwen2.5-coder:14b"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_TIMEOUT: int = 300
    MAX_CONCURRENT_AGENTS: int = 10
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Logging & Metrics
    LOG_LEVEL: str = "INFO"
    PROMETHEUS_ENABLED: bool = True
    AUDIT_LOG_ENABLED: bool = True
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
