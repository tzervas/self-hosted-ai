"""Google ADK Base Agent Implementation

Provides base classes for ADK-wrapped agents that use LiteLLM
for inference backend.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import httpx
from loguru import logger


class AgentPriority(str, Enum):
    """Request priority levels for GPU queue."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class ADKConfig:
    """Configuration for ADK agents.
    
    Attributes:
        name: Agent name for identification
        model: LLM model to use (routed via LiteLLM)
        litellm_url: LiteLLM proxy URL
        litellm_api_key: API key for LiteLLM
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens for generation
        timeout: Request timeout in seconds
        priority: Queue priority level
        system_prompt: Custom system prompt override
        retry_attempts: Number of retries on failure
        retry_delay: Delay between retries in seconds
    """
    name: str
    model: str = "qwen2.5-coder:14b"
    litellm_url: str = "http://localhost:4000"
    litellm_api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 300
    priority: AgentPriority = AgentPriority.NORMAL
    system_prompt: Optional[str] = None
    retry_attempts: int = 3
    retry_delay: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ADKResult:
    """Result from ADK agent execution.
    
    Attributes:
        agent_name: Name of the agent
        status: Execution status (success, error, timeout)
        output: Agent output content
        model_used: Actual model used
        tokens: Token usage statistics
        duration_seconds: Execution duration
        error: Error message if failed
        metadata: Additional result metadata
    """
    agent_name: str
    status: str
    output: Optional[str] = None
    model_used: Optional[str] = None
    tokens: Optional[Dict[str, int]] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        return self.status == "success"


class ADKAgent(ABC):
    """Base class for Google ADK-wrapped agents.
    
    This class provides the foundation for creating agents that:
    - Use LiteLLM as the inference backend
    - Support priority-based GPU queuing
    - Integrate with Google ADK for orchestration
    - Provide evaluation capabilities
    """
    
    def __init__(self, config: ADKConfig, http_client: Optional[httpx.AsyncClient] = None):
        """Initialize ADK agent.
        
        Args:
            config: Agent configuration
            http_client: Optional shared HTTP client
        """
        self.config = config
        self._client = http_client
        self._owns_client = http_client is None
        self.logger = logger.bind(agent=config.name)
    
    async def __aenter__(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_client and self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Agent not initialized. Use async context manager.")
        return self._client
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent type.
        
        Returns:
            System prompt string
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_agent_type(self) -> str:
        """Get the agent type identifier.
        
        Returns:
            Agent type string (e.g., 'development', 'code_review')
        """
        raise NotImplementedError
    
    def _build_messages(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Build message list for LLM call.
        
        Args:
            task: Task description
            context: Additional context
            history: Conversation history
            
        Returns:
            List of message dicts
        """
        system_prompt = self.config.system_prompt or self.get_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history if provided
        if history:
            messages.extend(history)
        
        # Build user message with context
        if context:
            context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            user_content = f"Context:\n{context_str}\n\nTask: {task}"
        else:
            user_content = task
        
        messages.append({"role": "user", "content": user_content})
        
        return messages
    
    async def _call_litellm(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Make a call to LiteLLM API.
        
        Args:
            messages: Message list
            **kwargs: Additional parameters
            
        Returns:
            API response dict
        """
        headers = {
            "Authorization": f"Bearer {self.config.litellm_api_key}",
            "Content-Type": "application/json",
            "X-Priority": self.config.priority.value
        }
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
            **kwargs
        }
        
        response = await self.client.post(
            f"{self.config.litellm_url}/v1/chat/completions",
            json=payload,
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"LiteLLM error: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> ADKResult:
        """Execute the agent with the given task.
        
        Args:
            task: Task description
            context: Additional context
            history: Conversation history
            
        Returns:
            ADKResult with execution outcome
        """
        start_time = time.time()
        self.logger.info(f"Executing task: {task[:100]}...")
        
        for attempt in range(self.config.retry_attempts):
            try:
                messages = self._build_messages(task, context, history)
                response = await self._call_litellm(messages)
                
                duration = time.time() - start_time
                output = response["choices"][0]["message"]["content"]
                usage = response.get("usage", {})
                
                self.logger.info(f"Task completed in {duration:.2f}s")
                
                return ADKResult(
                    agent_name=self.config.name,
                    status="success",
                    output=output,
                    model_used=response.get("model", self.config.model),
                    tokens={
                        "prompt": usage.get("prompt_tokens", 0),
                        "completion": usage.get("completion_tokens", 0),
                        "total": usage.get("total_tokens", 0)
                    },
                    duration_seconds=duration,
                    metadata={"attempt": attempt + 1}
                )
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Attempt {attempt + 1} timed out")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    return ADKResult(
                        agent_name=self.config.name,
                        status="timeout",
                        error="Request timed out after all retries",
                        duration_seconds=time.time() - start_time
                    )
                    
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    return ADKResult(
                        agent_name=self.config.name,
                        status="error",
                        error=str(e),
                        duration_seconds=time.time() - start_time
                    )
        
        # Should not reach here
        return ADKResult(
            agent_name=self.config.name,
            status="error",
            error="Unknown error",
            duration_seconds=time.time() - start_time
        )
    
    async def execute_streaming(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[str], None]] = None
    ) -> ADKResult:
        """Execute with streaming response.
        
        Args:
            task: Task description
            context: Additional context
            callback: Callback for each chunk
            
        Returns:
            ADKResult with full output
        """
        start_time = time.time()
        messages = self._build_messages(task, context)
        
        headers = {
            "Authorization": f"Bearer {self.config.litellm_api_key}",
            "Content-Type": "application/json",
            "X-Priority": self.config.priority.value
        }
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True
        }
        
        full_output = []
        
        async with self.client.stream(
            "POST",
            f"{self.config.litellm_url}/v1/chat/completions",
            json=payload,
            headers=headers
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            full_output.append(content)
                            if callback:
                                callback(content)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass
        
        return ADKResult(
            agent_name=self.config.name,
            status="success",
            output="".join(full_output),
            model_used=self.config.model,
            duration_seconds=time.time() - start_time
        )
