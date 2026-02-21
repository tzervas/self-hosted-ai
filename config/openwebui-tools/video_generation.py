"""
title: Video Generation Tool
description: Generate videos using Wan 2.1 T2V via ComfyUI direct API with progressive preview streaming. The LLM can call this tool when a user asks for video creation.
author: self-hosted-ai
version: 2.2.0
"""

import json
import logging
import random
import time
import urllib.parse

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Tools:
    class Valves(BaseModel):
        comfyui_base_url: str = Field(
            default="http://comfyui-self-hosted-ai-gpu-worker-comfyui.gpu-workloads:8188",
            description="ComfyUI API base URL",
        )
        timeout: int = Field(default=300, description="Request timeout in seconds")

    def __init__(self):
        self.valves = self.Valves()

    def check_generation_status(self, prompt_id: str) -> str:
        """
        Check the status of a video generation job and retrieve preview frames if available.
        Use this to monitor long-running video generations and view intermediate results.

        :param prompt_id: The prompt_id returned from generate_video()
        :return: Status message with progress details and preview URLs
        """
        try:
            # Check queue status
            queue_resp = requests.get(
                f"{self.valves.comfyui_base_url}/queue", timeout=10
            )
            queue_resp.raise_for_status()
            queue_data = queue_resp.json()

            # Check if still in queue
            running = queue_data.get("queue_running", [])
            pending = queue_data.get("queue_pending", [])

            for item in running:
                if item[1] == prompt_id:
                    return f"Video is currently generating (prompt_id: {prompt_id}). Check again in a moment for previews."

            for idx, item in enumerate(pending):
                if item[1] == prompt_id:
                    return f"Video is queued at position {idx + 1} (prompt_id: {prompt_id}). Waiting to start..."

            # Check history for completion
            hist_resp = requests.get(
                f"{self.valves.comfyui_base_url}/history/{prompt_id}", timeout=10
            )
            hist_resp.raise_for_status()
            hist = hist_resp.json()

            if prompt_id not in hist:
                return f"No status found for prompt_id: {prompt_id}. It may have been cleared from history."

            outputs = hist[prompt_id].get("outputs", {})
            status = hist[prompt_id].get("status", {})

            # Collect all image outputs (frames + previews)
            all_images = []
            preview_base = self.valves.comfyui_base_url.rstrip("/")

            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for img in node_output["images"]:
                        img_url = f"{preview_base}/view?filename={urllib.parse.quote(img['filename'])}"
                        all_images.append(
                            {
                                "filename": img["filename"],
                                "url": img_url,
                                "type": img.get("type", "output"),
                            }
                        )

            if all_images:
                frame_list = "\n".join(
                    [
                        f"  - {img['filename']} ({img['type']}): {img['url']}"
                        for img in all_images
                    ]
                )
                return (
                    f"Video generation completed!\n"
                    f"Status: {status.get('status_str', 'completed')}\n"
                    f"Frames generated: {len(all_images)}\n\n"
                    f"Preview URLs:\n{frame_list}\n\n"
                    f"View frames directly in your browser using the URLs above."
                )

            return f"Video generation completed but no output images found. Status: {status.get('status_str', 'unknown')}"

        except requests.exceptions.ConnectionError:
            return "ComfyUI is not reachable. Ensure the ComfyUI service is running."
        except Exception as e:
            return f"Error checking status: {str(e)}"

    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality, distorted, artifacts, watermark, text",
        frames: int = 33,
        width: int = 480,
        height: int = 320,
        steps: int = 20,
        seed: int = -1,
    ) -> str:
        """
        Generate a short video from a text description using Wan 2.1 (1.3B) via ComfyUI.
        Use this when the user asks you to create, generate, or make a video or animation.
        Outputs frames as individual images (video assembly requires VHS_VideoCombine custom node).

        :param prompt: Detailed description of the video to generate (be specific about motion and scene)
        :param negative_prompt: Things to avoid in the generated video
        :param frames: Number of frames (default 33, max 81). More frames = longer video but slower.
        :param width: Video width in pixels (default 480, max 720)
        :param height: Video height in pixels (default 320, max 480)
        :param steps: Sampling steps (default 20, higher = better quality but slower)
        :param seed: Random seed (-1 for random)
        :return: Status message with video generation details
        """
        if seed == -1:
            seed = random.randint(0, 2**31 - 1)

        # Clamp values to hardware-safe limits
        actual_width = min(width, 720)
        actual_height = min(height, 480)
        actual_frames = min(frames, 81)
        actual_steps = min(steps, 40)

        # Build Wan 2.1 T2V 1.3B workflow
        workflow = {
            "1": {
                "inputs": {
                    "unet_name": "wan2.1_t2v_1.3B_bf16.safetensors",
                    "weight_dtype": "default",
                },
                "class_type": "UNETLoader",
            },
            "2": {
                "inputs": {
                    "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                    "type": "wan",
                },
                "class_type": "CLIPLoader",
            },
            "3": {
                "inputs": {"vae_name": "wan_2.1_vae.safetensors"},
                "class_type": "VAELoader",
            },
            "4": {
                "inputs": {"text": prompt, "clip": ["2", 0]},
                "class_type": "CLIPTextEncode",
            },
            "5": {
                "inputs": {"text": negative_prompt, "clip": ["2", 0]},
                "class_type": "CLIPTextEncode",
            },
            "6": {
                "inputs": {
                    "width": actual_width,
                    "height": actual_height,
                    "length": actual_frames,
                    "batch_size": 1,
                },
                "class_type": "EmptyWanLatentVideo",
            },
            "7": {
                "inputs": {
                    "seed": seed,
                    "steps": actual_steps,
                    "cfg": 6.0,
                    "sampler_name": "uni_pc_bh2",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["6", 0],
                },
                "class_type": "KSampler",
            },
            "8": {
                "inputs": {"samples": ["7", 0], "vae": ["3", 0]},
                "class_type": "VAEDecode",
            },
            "9": {
                "inputs": {
                    "filename_prefix": "OpenWebUI_video",
                    "images": ["8", 0],
                },
                "class_type": "SaveImage",  # Exports individual frames; video assembly via VHS_VideoCombine if available
            },
        }

        try:
            response = requests.post(
                f"{self.valves.comfyui_base_url}/prompt",
                json={"prompt": workflow, "client_id": f"owui-vid-{seed}"},
                timeout=30,  # Prompt submission should return immediately
            )
            response.raise_for_status()
            result = response.json()
            prompt_id = result.get("prompt_id", "unknown")

            # Return immediately with progress monitoring instructions
            preview_base = self.valves.comfyui_base_url.rstrip("/")
            progress_url = f"{preview_base}/view"

            return (
                f"✅ Video generation started with Wan 2.1!\n\n"
                f"**Job Details:**\n"
                f"  - Prompt: '{prompt}'\n"
                f"  - Frames: {actual_frames}, Resolution: {actual_width}x{actual_height}\n"
                f"  - Steps: {actual_steps}, Seed: {seed}\n"
                f"  - Prompt ID: {prompt_id}\n\n"
                f"**Monitor Progress:**\n"
                f"  1. ComfyUI generates preview frames during generation\n"
                f"  2. View live progress at: {preview_base}/\n"
                f"  3. Estimated time: {int(actual_frames * actual_steps / 10)} seconds\n\n"
                f"**Check Status:**\n"
                f"  Ask me to 'check video generation status for {prompt_id}'\n"
                f"  I'll retrieve preview URLs for all generated frames.\n\n"
                f"Generation is running in the background. You can continue chatting while it completes."
            )

        except requests.exceptions.ConnectionError:
            return "ComfyUI is not reachable. Ensure the ComfyUI service is running and Wan 2.1 models are loaded."
        except Exception as e:
            return f"Error generating video: {str(e)}"
