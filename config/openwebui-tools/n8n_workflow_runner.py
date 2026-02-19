"""
title: n8n Workflow Runner
description: Execute n8n automation workflows from chat. Enables agentic multi-step pipelines including document processing, multi-agent orchestration, and chained workflows.
author: self-hosted-ai
version: 1.0.0
"""

import json
import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        n8n_base_url: str = Field(
            default="http://n8n.automation:5678",
            description="n8n base URL for webhook calls",
        )
        timeout: int = Field(default=120, description="Request timeout in seconds")

    def __init__(self):
        self.valves = self.Valves()

    def run_agent_chain(
        self,
        task: str,
        context: str = "",
        max_steps: int = 5,
    ) -> str:
        """
        Run a multi-agent reasoning chain via n8n. Use this for complex tasks requiring
        step-by-step reasoning, research, or multi-model collaboration.

        :param task: The task or question to solve
        :param context: Additional context or constraints for the task
        :param max_steps: Maximum reasoning steps (default 5)
        :return: Result of the agent chain execution
        """
        try:
            response = requests.post(
                f"{self.valves.n8n_base_url}/webhook/agent/reason",
                json={
                    "task": task,
                    "context": context,
                    "max_steps": min(max_steps, 10),
                    "model": "phi4:latest",
                },
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            result = response.json()
            return f"Agent chain result:\n{json.dumps(result, indent=2)}"
        except requests.exceptions.ConnectionError:
            return "n8n agent workflow is not available. Ensure the agentic-reasoning workflow is active."
        except Exception as e:
            return f"Error running agent chain: {str(e)}"

    def run_workflow(
        self,
        workflow_name: str,
        input_data: str = "{}",
    ) -> str:
        """
        Execute a named n8n workflow via webhook. Available workflows:
        - 'generate-image': Text-to-image generation
        - 'video/generate': Text-to-video generation
        - 'tts/generate': Text-to-speech
        - 'agent/reason': Multi-step reasoning
        - 'agents/orchestrate': Multi-agent orchestration
        - 'workflow/execute-chain': Generic multi-step pipeline
        - 'chat': Direct Ollama chat

        :param workflow_name: The webhook path of the workflow to execute
        :param input_data: JSON string of input data for the workflow
        :return: Workflow execution result
        """
        try:
            data = json.loads(input_data) if isinstance(input_data, str) else input_data
        except json.JSONDecodeError:
            data = {"text": input_data}

        try:
            response = requests.post(
                f"{self.valves.n8n_base_url}/webhook/{workflow_name}",
                json=data,
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            result = response.json()
            return f"Workflow '{workflow_name}' result:\n{json.dumps(result, indent=2)}"
        except requests.exceptions.ConnectionError:
            return f"n8n workflow '{workflow_name}' is not available. Check that the workflow is active in n8n."
        except Exception as e:
            return f"Error running workflow '{workflow_name}': {str(e)}"
