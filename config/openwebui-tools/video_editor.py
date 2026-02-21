"""
title: Video Editor
description: Edit videos (trim, cut, split, concatenate, resize, speed adjustment)
author: Self-Hosted AI Platform
author_url: https://github.com/tzervas/homelab-cluster
version: 1.0.0
license: MIT
"""

import os
import requests
import urllib.parse
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        """Configuration for video editing service"""

        video_server_url: str = Field(
            default="http://192.168.1.99:5005",
            description="Video processing server base URL"
        )
        max_file_size_mb: int = Field(
            default=500,
            description="Maximum video file size in MB"
        )

    def __init__(self):
        self.valves = self.Valves()

    def trim_video(
        self,
        video_url: str,
        start_time: str,
        end_time: str,
        __event_emitter__=None
    ) -> str:
        """
        Trim video to a specific time range.

        Args:
            video_url: URL or path to the input video
            start_time: Start time (format: "00:00:10" or "10" for seconds)
            end_time: End time (format: "00:01:30" or "90" for seconds)

        Returns:
            URL to the trimmed video

        Example:
            "Trim the video from 10 seconds to 1 minute 30 seconds"
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
            await emit_status(f"✂️ Trimming video from {start_time} to {end_time}...")

        try:
            response = requests.post(
                f"{self.valves.video_server_url}/edit/trim",
                json={
                    "video_url": video_url,
                    "start_time": start_time,
                    "end_time": end_time
                },
                timeout=300  # 5 minutes for processing
            )
            response.raise_for_status()

            result = response.json()
            output_url = result.get("output_url")

            if not output_url:
                return "❌ Error: Video server didn't return a valid URL"

            if __event_emitter__:
                await emit_status("✅ Video trimmed successfully!", done=True)

            return (
                f"✅ **Video Trimmed Successfully!**\n\n"
                f"**Time Range**: {start_time} → {end_time}\n"
                f"**Duration**: ~{result.get('duration', 'unknown')}s\n\n"
                f"🎬 **[Download Video]({output_url})**"
            )

        except requests.exceptions.Timeout:
            return "❌ Timeout: Video processing took too long (>5 minutes)"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to video server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"

    def concatenate_videos(
        self,
        video_urls: List[str],
        transition: Optional[Literal["none", "fade", "dissolve", "wipe"]] = "none",
        __event_emitter__=None
    ) -> str:
        """
        Concatenate multiple videos into one.

        Args:
            video_urls: List of video URLs/paths to join (in order)
            transition: Transition effect between clips

        Returns:
            URL to the concatenated video

        Example:
            "Join these 3 videos together with fade transitions"
        """

        async def emit_status(status: str, done: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        if len(video_urls) < 2:
            return "❌ Error: Need at least 2 videos to concatenate"

        if __event_emitter__:
            await emit_status(f"🎬 Joining {len(video_urls)} videos...")

        try:
            response = requests.post(
                f"{self.valves.video_server_url}/edit/concatenate",
                json={
                    "video_urls": video_urls,
                    "transition": transition
                },
                timeout=600  # 10 minutes for multiple videos
            )
            response.raise_for_status()

            result = response.json()
            output_url = result.get("output_url")

            if not output_url:
                return "❌ Error: Video server didn't return a valid URL"

            if __event_emitter__:
                await emit_status("✅ Videos joined successfully!", done=True)

            return (
                f"✅ **Videos Concatenated Successfully!**\n\n"
                f"**Clips**: {len(video_urls)}\n"
                f"**Transition**: {transition}\n"
                f"**Total Duration**: ~{result.get('duration', 'unknown')}s\n\n"
                f"🎬 **[Download Video]({output_url})**"
            )

        except requests.exceptions.Timeout:
            return "❌ Timeout: Video processing took too long"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to video server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"

    def resize_video(
        self,
        video_url: str,
        resolution: Literal[
            "1920x1080", "1280x720", "854x480", "640x360",
            "3840x2160", "2560x1440", "instagram", "tiktok", "youtube"
        ],
        __event_emitter__=None
    ) -> str:
        """
        Resize video to a specific resolution or platform preset.

        Args:
            video_url: URL or path to the input video
            resolution: Target resolution or platform (instagram=1080x1080, tiktok=1080x1920)

        Returns:
            URL to the resized video

        Example:
            "Resize this video for Instagram (1080x1080 square)"
        """

        async def emit_status(status: str, done: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        # Map platform presets to resolutions
        platform_presets = {
            "instagram": "1080x1080",
            "tiktok": "1080x1920",
            "youtube": "1920x1080"
        }

        final_resolution = platform_presets.get(resolution, resolution)

        if __event_emitter__:
            await emit_status(f"📐 Resizing video to {final_resolution}...")

        try:
            response = requests.post(
                f"{self.valves.video_server_url}/edit/resize",
                json={
                    "video_url": video_url,
                    "resolution": final_resolution
                },
                timeout=300
            )
            response.raise_for_status()

            result = response.json()
            output_url = result.get("output_url")

            if not output_url:
                return "❌ Error: Video server didn't return a valid URL"

            if __event_emitter__:
                await emit_status("✅ Video resized successfully!", done=True)

            return (
                f"✅ **Video Resized Successfully!**\n\n"
                f"**Resolution**: {final_resolution}\n"
                f"**Platform**: {resolution if resolution in platform_presets else 'custom'}\n"
                f"**File Size**: ~{result.get('file_size_mb', 'unknown')} MB\n\n"
                f"🎬 **[Download Video]({output_url})**"
            )

        except requests.exceptions.Timeout:
            return "❌ Timeout: Video processing took too long"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to video server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"

    def adjust_speed(
        self,
        video_url: str,
        speed: float,
        maintain_audio_pitch: bool = True,
        __event_emitter__=None
    ) -> str:
        """
        Adjust video playback speed (slow motion or timelapse).

        Args:
            video_url: URL or path to the input video
            speed: Speed multiplier (0.25=4x slower, 2.0=2x faster, etc.)
            maintain_audio_pitch: Keep audio pitch unchanged when speeding up/down

        Returns:
            URL to the speed-adjusted video

        Example:
            "Make this video play 2x faster" or "Create slow motion at 0.5x speed"
        """

        async def emit_status(status: str, done: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        # Validate speed range
        if speed <= 0 or speed > 10:
            return "❌ Error: Speed must be between 0.1 and 10.0"

        speed_description = "slow motion" if speed < 1 else "timelapse"

        if __event_emitter__:
            await emit_status(f"⏱️ Adjusting video speed to {speed}x ({speed_description})...")

        try:
            response = requests.post(
                f"{self.valves.video_server_url}/edit/speed",
                json={
                    "video_url": video_url,
                    "speed": speed,
                    "maintain_pitch": maintain_audio_pitch
                },
                timeout=300
            )
            response.raise_for_status()

            result = response.json()
            output_url = result.get("output_url")

            if not output_url:
                return "❌ Error: Video server didn't return a valid URL"

            if __event_emitter__:
                await emit_status("✅ Video speed adjusted!", done=True)

            return (
                f"✅ **Video Speed Adjusted!**\n\n"
                f"**Speed**: {speed}x ({speed_description})\n"
                f"**Audio Pitch**: {'preserved' if maintain_audio_pitch else 'changed'}\n"
                f"**New Duration**: ~{result.get('duration', 'unknown')}s\n\n"
                f"🎬 **[Download Video]({output_url})**"
            )

        except requests.exceptions.Timeout:
            return "❌ Timeout: Video processing took too long"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to video server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"
