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
        negative_prompt: str = "blurry, low quality, distorted, artifacts",
        frames: int = 24,
        fps: int = 8,
        width: int = 512,
        height: int = 512,
        model: str = "wan",
    ) -> str:
        """
        Generate a short video from a text description using AI video models via ComfyUI.
        Use this when the user asks you to create, generate, or make a video or animation.

        :param prompt: Detailed description of the video to generate
        :param negative_prompt: Things to avoid in the generated video
        :param frames: Number of frames to generate (default 24, max 120)
        :param fps: Frames per second (default 8)
        :param width: Video width in pixels (default 512)
        :param height: Video height in pixels (default 512)
        :param model: Video model to use - 'wan' (default) or 'svd'
        :return: Status message with video generation details
        """
        try:
            response = requests.post(
                self.valves.n8n_webhook_url,
                json={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "model": model,
                    "frames": min(frames, 120),
                    "fps": fps,
                    "width": min(width, 1024),
                    "height": min(height, 1024),
                    "guidance_scale": 7.5,
                },
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            result = response.json()

            status = result.get("status", "unknown")
            if status == "processing":
                return (
                    f"Video generation started! Model: {model}, Frames: {frames}, "
                    f"FPS: {fps}, Resolution: {width}x{height}. "
                    f"Prompt: '{prompt}'. "
                    f"Estimated time: ~{frames * 2} seconds. "
                    f"Request ID: {result.get('request_id', 'N/A')}"
                )
            elif status == "completed":
                return (
                    f"Video generated successfully! Model: {model}, "
                    f"Resolution: {result.get('resolution', f'{width}x{height}')}. "
                    f"Video URL: {result.get('video_url', 'available in outputs')}"
                )
            else:
                return f"Video generation response: {json.dumps(result)}"

        except requests.exceptions.ConnectionError:
            return "Video generation service is not available. Ensure the n8n video-generation workflow is active and ComfyUI has video models loaded."
        except Exception as e:
            return f"Error generating video: {str(e)}"
