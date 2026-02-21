"""
title: AI Image Upscaler
description: Upscale images 2x/4x using RealESRGAN AI upscaling
author: Self-Hosted AI Platform
author_url: https://github.com/tzervas/homelab-cluster
version: 1.0.0
license: MIT
"""

import os
import requests
import urllib.parse
from typing import Optional, Literal
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        """Configuration for image upscaling service"""

        comfyui_base_url: str = Field(
            default="http://192.168.1.99:8188",
            description="ComfyUI server base URL"
        )
        default_scale: int = Field(
            default=2,
            description="Default upscale factor (2 or 4)"
        )

    def __init__(self):
        self.valves = self.Valves()

    def upscale_image(
        self,
        image_url: str,
        scale: Literal[2, 4] = 2,
        denoise_strength: Optional[float] = 0.3,
        __event_emitter__=None
    ) -> str:
        """
        Upscale image using AI (RealESRGAN).

        Args:
            image_url: URL or path to the input image
            scale: Upscaling factor (2x or 4x)
            denoise_strength: Denoising strength (0.0-1.0, higher = more smoothing)

        Returns:
            URL to the upscaled image

        Example:
            "Upscale this image 4x with high quality"
        """

        async def emit_status(status: str, done: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        if scale not in [2, 4]:
            return "❌ Error: Scale must be 2 or 4"

        if __event_emitter__:
            await emit_status(f"🔍 Upscaling image {scale}x with AI...")

        try:
            # ComfyUI workflow for upscaling
            workflow = {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": image_url}
                },
                "2": {
                    "class_type": "UpscaleModelLoader",
                    "inputs": {
                        "model_name": f"RealESRGAN_x{scale}plus.pth"
                    }
                },
                "3": {
                    "class_type": "ImageUpscaleWithModel",
                    "inputs": {
                        "upscale_model": ["2", 0],
                        "image": ["1", 0]
                    }
                },
                "4": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "images": ["3", 0],
                        "filename_prefix": "upscaled"
                    }
                }
            }

            # Add denoising if requested
            if denoise_strength and denoise_strength > 0:
                workflow["5"] = {
                    "class_type": "ImageDenoise",
                    "inputs": {
                        "image": ["3", 0],
                        "strength": denoise_strength
                    }
                }
                workflow["4"]["inputs"]["images"] = ["5", 0]

            # Submit workflow to ComfyUI
            response = requests.post(
                f"{self.valves.comfyui_base_url}/prompt",
                json={"prompt": workflow},
                timeout=180
            )
            response.raise_for_status()

            result = response.json()
            prompt_id = result.get("prompt_id")

            if not prompt_id:
                return "❌ Error: Failed to start upscaling"

            if __event_emitter__:
                await emit_status("⏳ Processing upscale (this may take 30-60 seconds)...")

            # Poll for completion
            import time
            max_wait = 120  # 2 minutes max
            start_time = time.time()

            while time.time() - start_time < max_wait:
                history_resp = requests.get(
                    f"{self.valves.comfyui_base_url}/history/{prompt_id}",
                    timeout=10
                )

                if history_resp.status_code == 200:
                    history = history_resp.json()

                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})

                        # Find the SaveImage node output
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                images = node_output["images"]
                                if images:
                                    filename = images[0]["filename"]
                                    subfolder = images[0].get("subfolder", "")
                                    image_url = (
                                        f"{self.valves.comfyui_base_url}/view?"
                                        f"filename={urllib.parse.quote(filename)}"
                                    )
                                    if subfolder:
                                        image_url += f"&subfolder={urllib.parse.quote(subfolder)}"

                                    if __event_emitter__:
                                        await emit_status("✅ Upscaling complete!", done=True)

                                    return (
                                        f"✅ **Image Upscaled Successfully!**\n\n"
                                        f"**Scale**: {scale}x\n"
                                        f"**Denoising**: {denoise_strength or 'none'}\n"
                                        f"**Model**: RealESRGAN\n\n"
                                        f"🖼️ **[View/Download Image]({image_url})**\n\n"
                                        f"💡 *Tip: Right-click image to save at full resolution*"
                                    )

                time.sleep(2)  # Check every 2 seconds

            return "❌ Timeout: Upscaling took too long (>2 minutes)"

        except requests.exceptions.Timeout:
            return "❌ Timeout: Failed to connect to ComfyUI server"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to ComfyUI server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"

    def enhance_image(
        self,
        image_url: str,
        enhancement_type: Literal[
            "sharpen", "denoise", "color_enhance", "auto_enhance"
        ] = "auto_enhance",
        __event_emitter__=None
    ) -> str:
        """
        Enhance image quality (sharpen, denoise, color correction).

        Args:
            image_url: URL or path to the input image
            enhancement_type: Type of enhancement to apply

        Returns:
            URL to the enhanced image

        Example:
            "Enhance this image quality and sharpen details"
        """

        async def emit_status(status: str, done: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        if __event_emitter__:
            await emit_status(f"✨ Enhancing image ({enhancement_type})...")

        try:
            # Use ComfyUI for enhancement
            workflow = {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": image_url}
                },
                "2": {
                    "class_type": "ImageEnhancement",
                    "inputs": {
                        "image": ["1", 0],
                        "enhancement": enhancement_type
                    }
                },
                "3": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "images": ["2", 0],
                        "filename_prefix": "enhanced"
                    }
                }
            }

            response = requests.post(
                f"{self.valves.comfyui_base_url}/prompt",
                json={"prompt": workflow},
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            prompt_id = result.get("prompt_id")

            if not prompt_id:
                return "❌ Error: Failed to start enhancement"

            # Poll for completion (similar to upscale)
            import time
            max_wait = 60
            start_time = time.time()

            while time.time() - start_time < max_wait:
                history_resp = requests.get(
                    f"{self.valves.comfyui_base_url}/history/{prompt_id}",
                    timeout=10
                )

                if history_resp.status_code == 200:
                    history = history_resp.json()

                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})

                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                images = node_output["images"]
                                if images:
                                    filename = images[0]["filename"]
                                    subfolder = images[0].get("subfolder", "")
                                    image_url = (
                                        f"{self.valves.comfyui_base_url}/view?"
                                        f"filename={urllib.parse.quote(filename)}"
                                    )
                                    if subfolder:
                                        image_url += f"&subfolder={urllib.parse.quote(subfolder)}"

                                    if __event_emitter__:
                                        await emit_status("✅ Enhancement complete!", done=True)

                                    return (
                                        f"✅ **Image Enhanced Successfully!**\n\n"
                                        f"**Enhancement**: {enhancement_type}\n\n"
                                        f"🖼️ **[View/Download Image]({image_url})**"
                                    )

                time.sleep(1)

            return "❌ Timeout: Enhancement took too long"

        except requests.exceptions.RequestException as e:
            return f"❌ Error: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"
