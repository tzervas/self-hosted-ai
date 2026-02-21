"""
title: Background Remover
description: Remove or replace image backgrounds using AI segmentation
author: Self-Hosted AI Platform
author_url: https://github.com/tzervas/homelab-cluster
version: 1.0.0
license: MIT
"""

import os
import requests
import urllib.parse
from typing import Optional
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        """Configuration for background removal service"""

        comfyui_base_url: str = Field(
            default="http://192.168.1.99:8188",
            description="ComfyUI server base URL"
        )

    def __init__(self):
        self.valves = self.Valves()

    def remove_background(
        self,
        image_url: str,
        output_format: Optional[str] = "png",
        __event_emitter__=None
    ) -> str:
        """
        Remove background from image, leaving transparent PNG.

        Args:
            image_url: URL or path to the input image
            output_format: Output format (png for transparency)

        Returns:
            URL to the image with removed background

        Example:
            "Remove the background from this product photo"
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
            await emit_status("🎭 Removing background with AI...")

        try:
            # ComfyUI workflow for background removal
            workflow = {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": image_url}
                },
                "2": {
                    "class_type": "ImageSegmentation",
                    "inputs": {
                        "image": ["1", 0],
                        "model": "u2net"  # U²-Net for accurate segmentation
                    }
                },
                "3": {
                    "class_type": "ApplyMask",
                    "inputs": {
                        "image": ["1", 0],
                        "mask": ["2", 0],
                        "invert": False
                    }
                },
                "4": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "images": ["3", 0],
                        "filename_prefix": "no_bg",
                        "format": output_format
                    }
                }
            }

            response = requests.post(
                f"{self.valves.comfyui_base_url}/prompt",
                json={"prompt": workflow},
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            prompt_id = result.get("prompt_id")

            if not prompt_id:
                return "❌ Error: Failed to start background removal"

            if __event_emitter__:
                await emit_status("⏳ Processing segmentation...")

            # Poll for completion
            import time
            max_wait = 90
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
                                        await emit_status("✅ Background removed!", done=True)

                                    return (
                                        f"✅ **Background Removed Successfully!**\n\n"
                                        f"**Model**: U²-Net segmentation\n"
                                        f"**Format**: PNG with transparency\n\n"
                                        f"🖼️ **[View/Download Image]({image_url})**\n\n"
                                        f"💡 *Tip: Use this image on any background or in designs*"
                                    )

                time.sleep(2)

            return "❌ Timeout: Background removal took too long"

        except requests.exceptions.RequestException as e:
            return f"❌ Error: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"

    def replace_background(
        self,
        image_url: str,
        background_description: str,
        background_color: Optional[str] = None,
        __event_emitter__=None
    ) -> str:
        """
        Replace image background with a new generated background or solid color.

        Args:
            image_url: URL or path to the input image
            background_description: Description of new background (e.g., "beach sunset", "office interior")
            background_color: Hex color code for solid background (e.g., "#FFFFFF")

        Returns:
            URL to the image with replaced background

        Example:
            "Replace the background with a beach sunset scene"
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
            if background_color:
                await emit_status(f"🎨 Replacing background with {background_color}...")
            else:
                await emit_status(f"🖼️ Generating new background: {background_description}...")

        try:
            workflow = {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": image_url}
                },
                "2": {
                    "class_type": "ImageSegmentation",
                    "inputs": {
                        "image": ["1", 0],
                        "model": "u2net"
                    }
                }
            }

            # Generate or create new background
            if background_color:
                # Solid color background
                workflow["3"] = {
                    "class_type": "CreateColorBackground",
                    "inputs": {
                        "width": 1024,
                        "height": 1024,
                        "color": background_color
                    }
                }
            else:
                # Generate background with SDXL
                workflow["3"] = {
                    "class_type": "TextToImage",
                    "inputs": {
                        "prompt": background_description,
                        "model": "sdxl",
                        "width": 1024,
                        "height": 1024
                    }
                }

            # Composite foreground onto new background
            workflow["4"] = {
                "class_type": "CompositeImages",
                "inputs": {
                    "background": ["3", 0],
                    "foreground": ["1", 0],
                    "mask": ["2", 0]
                }
            }

            workflow["5"] = {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["4", 0],
                    "filename_prefix": "replaced_bg"
                }
            }

            response = requests.post(
                f"{self.valves.comfyui_base_url}/prompt",
                json={"prompt": workflow},
                timeout=180
            )
            response.raise_for_status()

            result = response.json()
            prompt_id = result.get("prompt_id")

            if not prompt_id:
                return "❌ Error: Failed to start background replacement"

            # Poll for completion
            import time
            max_wait = 120
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
                                        await emit_status("✅ Background replaced!", done=True)

                                    bg_type = f"color: {background_color}" if background_color else background_description

                                    return (
                                        f"✅ **Background Replaced Successfully!**\n\n"
                                        f"**New Background**: {bg_type}\n\n"
                                        f"🖼️ **[View/Download Image]({image_url})**"
                                    )

                time.sleep(2)

            return "❌ Timeout: Background replacement took too long"

        except requests.exceptions.RequestException as e:
            return f"❌ Error: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"
