"""Google ADK Agent Wrappers

Wraps existing specialized agents with Google ADK for orchestration,
evaluation, and multi-agent workflows.
"""

import asyncio
import time
from typing import Any, Dict, Optional

import httpx


# =============================================================================
# ADK Agent Wrapper
# =============================================================================

async def invoke_adk_agent(
    agent_type: str,
    task: str,
    context: Optional[Dict[str, Any]],
    model: str,
    temperature: float,
    timeout: int,
    priority: str,
    http_client: httpx.AsyncClient,
    litellm_url: str,
    litellm_key: str
) -> Dict[str, Any]:
    """Invoke an agent via Google ADK with LiteLLM backend.
    
    Args:
        agent_type: Type of agent to invoke
        task: Task description
        context: Additional context
        model: Model to use
        temperature: Sampling temperature
        timeout: Request timeout
        priority: Request priority (high/normal/low)
        http_client: HTTP client
        litellm_url: LiteLLM proxy URL
        litellm_key: LiteLLM API key
        
    Returns:
        Agent execution result
    """
    # Get system prompt based on agent type
    system_prompt = get_agent_system_prompt(agent_type)
    
    # Build messages
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add context if provided
    if context:
        context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
        messages.append({
            "role": "user",
            "content": f"Context:\n{context_str}\n\nTask: {task}"
        })
    else:
        messages.append({"role": "user", "content": task})
    
    # Call LiteLLM
    start_time = time.time()
    
    headers = {
        "Authorization": f"Bearer {litellm_key}",
        "Content-Type": "application/json",
        "X-Priority": priority  # Custom header for queue priority
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": False
    }
    
    response = await http_client.post(
        f"{litellm_url}/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=timeout
    )
    
    if response.status_code != 200:
        raise Exception(f"LiteLLM error: {response.status_code} - {response.text}")
    
    result = response.json()
    duration = time.time() - start_time
    
    # Extract response
    output = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})
    
    return {
        "output": output,
        "model_used": result.get("model", model),
        "tokens": {
            "prompt": usage.get("prompt_tokens", 0),
            "completion": usage.get("completion_tokens", 0),
            "total": usage.get("total_tokens", 0)
        },
        "duration": duration
    }


async def execute_adk_workflow(
    workflow_name: str,
    inputs: Dict[str, Any],
    priority: str,
    http_client: httpx.AsyncClient,
    litellm_url: str,
    litellm_key: str
) -> Dict[str, Any]:
    """Execute a multi-agent workflow.
    
    Workflows are defined in the workflows/ directory and orchestrated
    using Google ADK's multi-agent capabilities.
    """
    from pathlib import Path
    import yaml
    
    # Load workflow definition
    workflows_dir = Path(__file__).parent.parent.parent / "workflows"
    workflow_file = workflows_dir / f"{workflow_name}.yaml"
    
    if not workflow_file.exists():
        raise ValueError(f"Workflow not found: {workflow_name}")
    
    with open(workflow_file) as f:
        workflow_def = yaml.safe_load(f)
    
    start_time = time.time()
    outputs = {}
    
    # Execute tasks in dependency order
    tasks = workflow_def.get("tasks", [])
    completed = set()
    
    while len(completed) < len(tasks):
        # Find tasks ready to execute (dependencies satisfied)
        ready = []
        for task in tasks:
            task_id = task["id"]
            if task_id in completed:
                continue
            
            deps = task.get("depends_on", [])
            if all(d in completed for d in deps):
                ready.append(task)
        
        if not ready:
            raise Exception("Circular dependency detected in workflow")
        
        # Execute ready tasks in parallel
        async def execute_task(task_def):
            agent_type = task_def.get("agent_type", "development")
            task_prompt = task_def["prompt"]
            
            # Substitute inputs and previous outputs
            for key, value in inputs.items():
                task_prompt = task_prompt.replace(f"{{{{ inputs.{key} }}}}", str(value))
            for key, value in outputs.items():
                task_prompt = task_prompt.replace(f"{{{{ outputs.{key} }}}}", str(value))
            
            result = await invoke_adk_agent(
                agent_type=agent_type,
                task=task_prompt,
                context=task_def.get("context"),
                model=task_def.get("model", "qwen2.5-coder:14b"),
                temperature=task_def.get("temperature", 0.7),
                timeout=task_def.get("timeout", 300),
                priority=priority,
                http_client=http_client,
                litellm_url=litellm_url,
                litellm_key=litellm_key
            )
            
            return task_def["id"], result
        
        results = await asyncio.gather(*[execute_task(t) for t in ready])
        
        for task_id, result in results:
            outputs[task_id] = result["output"]
            completed.add(task_id)
    
    duration = time.time() - start_time
    
    return {
        "status": "completed",
        "outputs": outputs,
        "duration": duration
    }


def get_agent_system_prompt(agent_type: str) -> str:
    """Get the system prompt for an agent type."""
    prompts = {
        "development": """You are an expert software developer. Your task is to write high-quality, 
production-ready code. Follow best practices for the language/framework being used.
Include proper error handling, documentation, and tests where appropriate.
Be concise and focus on the implementation.""",

        "code_review": """You are an expert code reviewer. Analyze the provided code for:
1. Code quality and best practices
2. Potential bugs and security vulnerabilities  
3. Performance issues
4. Maintainability and readability

Provide specific, actionable feedback with examples. Rate the code on a scale of 1-10.""",

        "testing": """You are an expert software tester. Generate comprehensive tests that cover:
1. Happy path scenarios
2. Edge cases and boundary conditions
3. Error handling
4. Integration points

Use appropriate testing frameworks and follow testing best practices.""",

        "documentation": """You are an expert technical writer. Create clear, comprehensive documentation that includes:
1. Overview and purpose
2. Installation/setup instructions
3. Usage examples with code
4. API reference (if applicable)
5. Troubleshooting guide

Use proper Markdown formatting and keep it concise yet thorough.""",

        "research": """You are an expert researcher. Analyze the topic thoroughly and provide:
1. Key findings and insights
2. Supporting evidence
3. Different perspectives
4. Recommendations

Be objective, cite sources where possible, and structure your findings clearly.""",

        "multimodal": """You are an expert in processing multimodal content (images, audio, video, text).
Analyze the provided content and extract relevant information, patterns, and insights.
Provide structured output suitable for further processing."""
    }
    
    return prompts.get(agent_type, prompts["development"])
