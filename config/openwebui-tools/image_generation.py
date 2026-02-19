"""
title: Image Generation Tool
description: Generate images using ComfyUI via n8n webhook. The LLM can call this tool when a user asks for image creation.
author: self-hosted-ai
version: 1.0.0
"""

import json
import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        n8n_webhook_url: str = Field(
            default="http://n8n.automation:5678/webhook/generate-image",
            description="n8n webhook URL for image generation",
        )
        comfyui_base_url: str = Field(
            default="http://comfyui-self-hosted-ai-gpu-worker-comfyui.gpu-workloads:8188",
            description="ComfyUI API base URL for retrieving images",
        )
        default_steps: int = Field(default=25, description="Default sampling steps")
        default_cfg: float = Field(default=7.5, description="Default CFG scale")
        timeout: int = Field(default=120, description="Request timeout in seconds")

    def __init__(self):
        self.valves = self.Valves()

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "blurry, bad quality, distorted, ugly, deformed",
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        seed: int = -1,
    ) -> str:
        """
        Generate an image from a text description using Stable Diffusion XL via ComfyUI.
        Use this when the user asks you to create, draw, generate, or make an image or picture.

        :param prompt: Detailed description of the image to generate
        :param negative_prompt: Things to avoid in the generated image
        :param width: Image width in pixels (default 1024)
        :param height: Image height in pixels (default 1024)
        :param steps: Number of sampling steps (default 25, higher = better quality but slower)
        :param seed: Random seed (-1 for random)
        :return: Status message with image details
        """
        import random

        if seed == -1:
            seed = random.randint(0, 2**32 - 1)

        # Build the SDXL workflow
        workflow = {
            "3": {
                "inputs": {
                    "seed": seed,
                    "steps": min(steps, 50),
                    "cfg": self.valves.default_cfg,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
                "class_type": "KSampler",
            },
            "4": {
                "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
                "class_type": "CheckpointLoaderSimple",
            },
            "5": {
                "inputs": {
                    "width": min(width, 2048),
                    "height": min(height, 2048),
                    "batch_size": 1,
                },
                "class_type": "EmptyLatentImage",
            },
            "6": {
                "inputs": {"text": prompt, "clip": ["4", 1]},
                "class_type": "CLIPTextEncode",
            },
            "7": {
                "inputs": {"text": negative_prompt, "clip": ["4", 1]},
                "class_type": "CLIPTextEncode",
            },
            "8": {
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
                "class_type": "VAEDecode",
            },
            "9": {
                "inputs": {"filename_prefix": "OpenWebUI", "images": ["8", 0]},
                "class_type": "SaveImage",
            },
        }

        try:
            # Submit to ComfyUI via n8n webhook
            response = requests.post(
                self.valves.n8n_webhook_url,
                json={"workflow": workflow, "client_id": f"owui-{seed}"},
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") == "pending":
                return f"Image generation queued (prompt_id: {result.get('prompt_id')}). It may take 30-60 seconds to complete. Prompt: '{prompt}' at {width}x{height}, {steps} steps, seed {seed}."

            return f"Image generated successfully! Prompt: '{prompt}', Size: {width}x{height}, Steps: {steps}, Seed: {seed}. Result: {json.dumps(result)}"

        except requests.exceptions.ConnectionError:
            # Fall back to direct ComfyUI API
            try:
                response = requests.post(
                    f"{self.valves.comfyui_base_url}/prompt",
                    json={"prompt": workflow, "client_id": f"owui-{seed}"},
                    timeout=self.valves.timeout,
                )
                response.raise_for_status()
                result = response.json()
                return f"Image queued directly to ComfyUI (prompt_id: {result.get('prompt_id')}). Generating '{prompt}' at {width}x{height}, {steps} steps."
            except Exception as e:
                return f"Error connecting to image generation service: {str(e)}"
        except Exception as e:
            return f"Error generating image: {str(e)}"
