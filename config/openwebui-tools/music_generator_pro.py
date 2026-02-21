"""
title: Professional Music Generator
description: Generate music with professional controls (genre, tempo, key, instrumentation, mood)
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
        """Configuration for music generation service"""

        audio_server_url: str = Field(
            default="http://192.168.1.99:5004",
            description="Audio generation server base URL"
        )
        default_duration: int = Field(
            default=30,
            description="Default music duration in seconds (10-120)"
        )
        default_tempo: int = Field(
            default=120,
            description="Default tempo in BPM (60-200)"
        )

    def __init__(self):
        self.valves = self.Valves()

    def generate_music(
        self,
        description: str,
        genre: Optional[Literal[
            "electronic", "edm", "house", "dubstep", "ambient", "cinematic",
            "orchestral", "epic", "rock", "metal", "acoustic", "jazz",
            "blues", "hiphop", "trap", "lofi", "pop", "classical"
        ]] = None,
        tempo: Optional[int] = None,
        key: Optional[Literal[
            "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
            "Cm", "C#m", "Dm", "D#m", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "A#m", "Bm"
        ]] = None,
        mood: Optional[Literal[
            "happy", "sad", "energetic", "calm", "dark", "uplifting",
            "mysterious", "dramatic", "peaceful", "aggressive"
        ]] = None,
        duration: Optional[int] = None,
        __event_emitter__=None
    ) -> str:
        """
        Generate professional music with detailed controls.

        Args:
            description: Natural language description of the music
            genre: Musical genre (electronic, orchestral, jazz, etc.)
            tempo: Beats per minute (60-200, default 120)
            key: Musical key (C, Dm, F#, etc.)
            mood: Emotional mood of the music
            duration: Length in seconds (10-120, default 30)

        Returns:
            URL to the generated audio file

        Example:
            "Generate 2 minutes of upbeat electronic music in D minor at 128 BPM"
        """

        async def emit_status(status: str, done: bool = False):
            """Emit status updates to the chat UI"""
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        # Build enhanced prompt with all parameters
        prompt_parts = [description]

        if genre:
            prompt_parts.append(f"Genre: {genre}")
        if mood:
            prompt_parts.append(f"Mood: {mood}")
        if key:
            prompt_parts.append(f"Key: {key}")

        enhanced_prompt = ", ".join(prompt_parts)

        # Use provided values or defaults
        final_tempo = tempo if tempo is not None else self.valves.default_tempo
        final_duration = duration if duration is not None else self.valves.default_duration

        # Validate ranges
        final_tempo = max(60, min(200, final_tempo))
        final_duration = max(10, min(120, final_duration))

        if __event_emitter__:
            await emit_status(
                f"🎵 Generating {final_duration}s of music at {final_tempo} BPM..."
            )

        try:
            # Call audio server music generation endpoint
            response = requests.post(
                f"{self.valves.audio_server_url}/generate/music",
                json={
                    "prompt": enhanced_prompt,
                    "duration": final_duration,
                    "tempo": final_tempo,
                    "model": "musicgen-medium"  # Use medium model for quality
                },
                timeout=180  # 3 minutes for music generation
            )
            response.raise_for_status()

            result = response.json()
            audio_url = result.get("audio_url")

            if not audio_url:
                return "❌ Error: Audio server didn't return a valid URL"

            if __event_emitter__:
                await emit_status("✅ Music generation complete!", done=True)

            return (
                f"✅ **Music Generated Successfully!**\n\n"
                f"**Description**: {enhanced_prompt}\n"
                f"**Duration**: {final_duration}s | **Tempo**: {final_tempo} BPM\n"
                f"**Genre**: {genre or 'auto'} | **Mood**: {mood or 'auto'}\n"
                f"**Key**: {key or 'auto'}\n\n"
                f"🔊 **[Play/Download Audio]({audio_url})**\n\n"
                f"💡 *Tip: Download and use in DAW for further production*"
            )

        except requests.exceptions.Timeout:
            return (
                "❌ **Timeout Error**\n\n"
                "Music generation took too long (>3 minutes).\n"
                "Try reducing duration or simplifying the prompt."
            )
        except requests.exceptions.RequestException as e:
            return f"❌ **Error**: Failed to connect to audio server: {str(e)}"
        except Exception as e:
            return f"❌ **Unexpected Error**: {str(e)}"

    def generate_sfx(
        self,
        description: str,
        duration: Optional[int] = None,
        category: Optional[Literal[
            "nature", "mechanical", "electronic", "impact", "ambient",
            "ui", "sci-fi", "horror", "industrial", "household"
        ]] = None,
        __event_emitter__=None
    ) -> str:
        """
        Generate sound effects from text description.

        Args:
            description: Natural language description of the sound
            duration: Length in seconds (1-30, default 5)
            category: Sound effect category

        Returns:
            URL to the generated audio file

        Example:
            "Generate a futuristic laser gun sound effect"
        """

        async def emit_status(status: str, done: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        # Build enhanced prompt
        prompt_parts = [description]
        if category:
            prompt_parts.append(f"Category: {category}")

        enhanced_prompt = ", ".join(prompt_parts)
        final_duration = min(30, max(1, duration or 5))

        if __event_emitter__:
            await emit_status(f"🔊 Generating {final_duration}s sound effect...")

        try:
            response = requests.post(
                f"{self.valves.audio_server_url}/generate/sfx",
                json={
                    "prompt": enhanced_prompt,
                    "duration": final_duration,
                    "model": "audioldm2-large"  # Use AudioLDM2 for SFX
                },
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            audio_url = result.get("audio_url")

            if not audio_url:
                return "❌ Error: Audio server didn't return a valid URL"

            if __event_emitter__:
                await emit_status("✅ Sound effect generated!", done=True)

            return (
                f"✅ **Sound Effect Generated!**\n\n"
                f"**Description**: {enhanced_prompt}\n"
                f"**Duration**: {final_duration}s\n"
                f"**Category**: {category or 'auto'}\n\n"
                f"🔊 **[Play/Download Audio]({audio_url})**"
            )

        except requests.exceptions.Timeout:
            return "❌ Timeout: SFX generation took too long"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to audio server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"
