"""
title: Audio Processor
description: Separate audio stems, apply effects, and master audio tracks
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
        """Configuration for audio processing service"""

        audio_server_url: str = Field(
            default="http://192.168.1.99:5004",
            description="Audio processing server base URL"
        )

    def __init__(self):
        self.valves = self.Valves()

    def separate_stems(
        self,
        audio_url: str,
        model: Literal["2stems", "4stems", "5stems"] = "4stems",
        __event_emitter__=None
    ) -> str:
        """
        Separate audio into individual stems (vocals, drums, bass, other).

        Args:
            audio_url: URL or path to the audio file
            model: Separation model (2stems=vocals/accompaniment, 4stems=vocals/drums/bass/other, 5stems=5-track)

        Returns:
            URLs to the separated stem files

        Example:
            "Separate this song into vocal, drum, bass, and other tracks"
        """

        async def emit_status(status: str, done: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        stem_configs = {
            "2stems": ["vocals", "accompaniment"],
            "4stems": ["vocals", "drums", "bass", "other"],
            "5stems": ["vocals", "drums", "bass", "piano", "other"]
        }

        stems = stem_configs.get(model, stem_configs["4stems"])

        if __event_emitter__:
            await emit_status(f"🎵 Separating audio into {len(stems)} stems using Demucs...")

        try:
            response = requests.post(
                f"{self.valves.audio_server_url}/process/separate",
                json={
                    "audio_url": audio_url,
                    "model": f"htdemucs_{model}",  # Use Hybrid Transformer Demucs
                    "shifts": 1,  # Higher shifts = better quality, slower
                    "overlap": 0.25
                },
                timeout=600  # 10 minutes for separation
            )
            response.raise_for_status()

            result = response.json()
            stem_urls = result.get("stems", {})

            if not stem_urls:
                return "❌ Error: Audio server didn't return stem URLs"

            if __event_emitter__:
                await emit_status("✅ Stem separation complete!", done=True)

            # Format output with all stems
            output_lines = [
                "✅ **Audio Stems Separated Successfully!**\n",
                f"**Model**: Demucs {model}",
                f"**Stems**: {len(stems)}\n"
            ]

            for stem_name in stems:
                if stem_name in stem_urls:
                    stem_url = stem_urls[stem_name]
                    output_lines.append(f"🎵 **{stem_name.title()}**: [Download]({stem_url})")

            output_lines.append(
                "\n💡 *Tip: Import stems into your DAW for remixing or karaoke*"
            )

            return "\n".join(output_lines)

        except requests.exceptions.Timeout:
            return "❌ Timeout: Stem separation took too long (>10 minutes)"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to audio server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"

    def apply_effects(
        self,
        audio_url: str,
        effect_type: Literal[
            "reverb", "delay", "compression", "eq", "normalize", "fade"
        ],
        parameters: Optional[dict] = None,
        __event_emitter__=None
    ) -> str:
        """
        Apply audio effects (reverb, delay, compression, EQ, etc.).

        Args:
            audio_url: URL or path to the audio file
            effect_type: Type of effect to apply
            parameters: Effect-specific parameters (e.g., {"room_size": 0.7, "wet_dry": 0.3} for reverb)

        Returns:
            URL to the processed audio

        Example:
            "Add reverb to this vocal track with large room size"
        """

        async def emit_status(status: str, done: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        # Default parameters for each effect
        default_params = {
            "reverb": {"room_size": 0.5, "decay_time": 2.0, "wet_dry": 0.3},
            "delay": {"delay_time": 0.5, "feedback": 0.4, "wet_dry": 0.3},
            "compression": {"threshold": -20, "ratio": 4, "attack": 0.01, "release": 0.1},
            "eq": {"low_gain": 0, "mid_gain": 0, "high_gain": 0},
            "normalize": {"target_db": -14},
            "fade": {"fade_in": 0.5, "fade_out": 0.5}
        }

        final_params = default_params.get(effect_type, {})
        if parameters:
            final_params.update(parameters)

        if __event_emitter__:
            await emit_status(f"🎚️ Applying {effect_type} effect...")

        try:
            response = requests.post(
                f"{self.valves.audio_server_url}/process/effects",
                json={
                    "audio_url": audio_url,
                    "effect": effect_type,
                    "parameters": final_params
                },
                timeout=180
            )
            response.raise_for_status()

            result = response.json()
            output_url = result.get("output_url")

            if not output_url:
                return "❌ Error: Audio server didn't return a valid URL"

            if __event_emitter__:
                await emit_status("✅ Effect applied!", done=True)

            # Format parameters for display
            params_display = ", ".join([f"{k}: {v}" for k, v in final_params.items()])

            return (
                f"✅ **Audio Effect Applied!**\n\n"
                f"**Effect**: {effect_type}\n"
                f"**Parameters**: {params_display}\n\n"
                f"🔊 **[Play/Download Audio]({output_url})**"
            )

        except requests.exceptions.Timeout:
            return "❌ Timeout: Effect processing took too long"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to audio server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"

    def master_audio(
        self,
        audio_url: str,
        target_loudness: Literal["-14 LUFS", "-9 LUFS", "-16 LUFS"] = "-14 LUFS",
        apply_limiting: bool = True,
        stereo_enhancement: bool = True,
        __event_emitter__=None
    ) -> str:
        """
        Master audio track for streaming/CD (EQ, compression, limiting, loudness normalization).

        Args:
            audio_url: URL or path to the audio file
            target_loudness: Target LUFS (-14 for streaming, -9 for CD, -16 for podcast)
            apply_limiting: Apply final limiter to prevent clipping
            stereo_enhancement: Enhance stereo width

        Returns:
            URL to the mastered audio

        Example:
            "Master this track for Spotify streaming (-14 LUFS)"
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
            await emit_status("🎛️ Mastering audio (EQ → compression → limiting → normalization)...")

        try:
            response = requests.post(
                f"{self.valves.audio_server_url}/process/master",
                json={
                    "audio_url": audio_url,
                    "target_lufs": float(target_loudness.split()[0]),
                    "limiting": apply_limiting,
                    "stereo_enhancement": stereo_enhancement,
                    "pipeline": [
                        {"type": "eq", "params": {"low_shelf": 0, "high_shelf": 0.5}},
                        {"type": "multiband_compression"},
                        {"type": "limiter", "params": {"threshold": -0.5, "release": 0.05}},
                        {"type": "loudness_normalize"}
                    ]
                },
                timeout=300
            )
            response.raise_for_status()

            result = response.json()
            output_url = result.get("output_url")
            measured_lufs = result.get("measured_lufs", "unknown")

            if not output_url:
                return "❌ Error: Audio server didn't return a valid URL"

            if __event_emitter__:
                await emit_status("✅ Mastering complete!", done=True)

            platform = "Spotify/Apple Music" if target_loudness == "-14 LUFS" else "CD/Hi-Fi" if target_loudness == "-9 LUFS" else "Podcast"

            return (
                f"✅ **Audio Mastered Successfully!**\n\n"
                f"**Target Loudness**: {target_loudness} ({platform})\n"
                f"**Measured LUFS**: {measured_lufs}\n"
                f"**Limiting**: {'enabled' if apply_limiting else 'disabled'}\n"
                f"**Stereo Enhancement**: {'enabled' if stereo_enhancement else 'disabled'}\n\n"
                f"🔊 **[Play/Download Mastered Audio]({output_url})**\n\n"
                f"💡 *Pipeline*: EQ → Multiband Compression → Limiter → Loudness Normalization"
            )

        except requests.exceptions.Timeout:
            return "❌ Timeout: Mastering took too long (>5 minutes)"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to audio server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"

    def convert_audio(
        self,
        audio_url: str,
        output_format: Literal["mp3", "wav", "flac", "ogg", "m4a"],
        bitrate: Optional[int] = None,
        __event_emitter__=None
    ) -> str:
        """
        Convert audio to different format (MP3, WAV, FLAC, OGG, M4A).

        Args:
            audio_url: URL or path to the audio file
            output_format: Target format
            bitrate: Bitrate in kbps (for lossy formats like MP3, default 320)

        Returns:
            URL to the converted audio

        Example:
            "Convert this to high-quality MP3 at 320kbps"
        """

        async def emit_status(status: str, done: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": status, "done": done}
                    }
                )

        # Default bitrates
        default_bitrates = {
            "mp3": 320,
            "ogg": 256,
            "m4a": 256
        }

        final_bitrate = bitrate if bitrate else default_bitrates.get(output_format)

        if __event_emitter__:
            await emit_status(f"🔄 Converting to {output_format.upper()}...")

        try:
            response = requests.post(
                f"{self.valves.audio_server_url}/process/convert",
                json={
                    "audio_url": audio_url,
                    "format": output_format,
                    "bitrate": final_bitrate
                },
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            output_url = result.get("output_url")

            if not output_url:
                return "❌ Error: Audio server didn't return a valid URL"

            if __event_emitter__:
                await emit_status("✅ Conversion complete!", done=True)

            bitrate_info = f" @ {final_bitrate}kbps" if final_bitrate else ""

            return (
                f"✅ **Audio Converted Successfully!**\n\n"
                f"**Format**: {output_format.upper()}{bitrate_info}\n"
                f"**File Size**: ~{result.get('file_size_mb', 'unknown')} MB\n\n"
                f"🔊 **[Download Converted Audio]({output_url})**"
            )

        except requests.exceptions.Timeout:
            return "❌ Timeout: Conversion took too long"
        except requests.exceptions.RequestException as e:
            return f"❌ Error: Failed to connect to audio server: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"
