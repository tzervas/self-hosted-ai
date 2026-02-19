"""
title: Video Generation Tool
description: Generate videos using ComfyUI via n8n webhook. The LLM can call this tool when a user asks for video creation.
author: self-hosted-ai
version: 1.0.0
"""

import json
import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        n8n_webhook_url: str = Field(
            default="http://n8n.automation:5678/webhook/video/generate",
            description="n8n webhook URL for video generation",
        )
        timeout: int = Field(default=300, description="Request timeout in seconds")

    def __init__(self):
        self.valves = self.Valves()

    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality, distorted, artifacts, watermark, text",
        frames: int = 33,
        width: int = 480,
        height: int = 320,
        steps: int = 20,
    ) -> str:
        """
        Generate a short video from a text description using Wan 2.1 (1.3B) via ComfyUI.
        Use this when the user asks you to create, generate, or make a video or animation.
        Outputs frames as images that form the video sequence.

        :param prompt: Detailed description of the video to generate (be specific about motion and scene)
        :param negative_prompt: Things to avoid in the generated video
        :param frames: Number of frames (default 33, max 81). More frames = longer video but slower.
        :param width: Video width in pixels (default 480, max 720)
        :param height: Video height in pixels (default 320, max 480)
        :param steps: Sampling steps (default 20, higher = better quality but slower)
        :return: Status message with video generation details
        """
        try:
            response = requests.post(
                self.valves.n8n_webhook_url,
                json={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "frames": min(frames, 81),
                    "width": min(width, 720),
                    "height": min(height, 480),
                    "steps": steps,
                    "cfg": 6.0,
                },
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            result = response.json()

            status = result.get("status", "unknown")
            if status == "processing":
                return (
                    f"Video generation started using Wan 2.1 T2V 1.3B! "
                    f"Frames: {frames}, Resolution: {width}x{height}, Steps: {steps}. "
                    f"Prompt: '{prompt}'. "
                    f"This may take 1-3 minutes. "
                    f"Request ID: {result.get('request_id', 'N/A')}"
                )
            elif status == "completed":
                return (
                    f"Video generated successfully with Wan 2.1! "
                    f"Frames: {result.get('frames_generated', frames)}, "
                    f"Resolution: {result.get('resolution', f'{width}x{height}')}. "
                    f"{result.get('message', '')}"
                )
            else:
                return f"Video generation response: {json.dumps(result)}"

        except requests.exceptions.ConnectionError:
            return "Video generation service is not available. Ensure the n8n video-generation workflow is active and ComfyUI has Wan 2.1 models loaded."
        except Exception as e:
            return f"Error generating video: {str(e)}"
