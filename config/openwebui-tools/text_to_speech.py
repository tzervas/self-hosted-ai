"""
title: Text to Speech Tool
description: Convert text to spoken audio using TTS models via n8n webhook. The LLM can call this when a user asks for audio narration.
author: self-hosted-ai
version: 1.0.0
"""

import json
import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        n8n_webhook_url: str = Field(
            default="http://n8n.automation:5678/webhook/tts/generate",
            description="n8n webhook URL for TTS generation",
        )
        timeout: int = Field(default=180, description="Request timeout in seconds")

    def __init__(self):
        self.valves = self.Valves()

    def text_to_speech(
        self,
        text: str,
        voice: str = "en_speaker_0",
        language: str = "en",
        speed: float = 1.0,
    ) -> str:
        """
        Convert text to spoken audio using AI text-to-speech models.
        Use this when the user asks you to read text aloud, generate speech, narrate, or create audio from text.

        :param text: The text to convert to speech (max 10000 characters)
        :param voice: Voice preset to use (default: en_speaker_0)
        :param language: Language code (default: en)
        :param speed: Speech speed multiplier (default: 1.0, range 0.5-2.0)
        :return: Status message with audio generation details
        """
        if len(text) > 10000:
            return "Error: Text exceeds maximum length of 10,000 characters. Please shorten the text."

        try:
            response = requests.post(
                self.valves.n8n_webhook_url,
                json={
                    "text": text,
                    "voice": voice,
                    "language": language,
                    "model": "xtts-v2",
                    "speed": max(0.5, min(speed, 2.0)),
                    "format": "wav",
                },
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                duration = result.get("duration_seconds", "unknown")
                return (
                    f"Audio generated successfully! "
                    f"Text length: {len(text)} characters, "
                    f"Voice: {voice}, Language: {language}, "
                    f"Duration: {duration}s. "
                    f"Audio URL: {result.get('audio_url', 'embedded in response')}"
                )
            else:
                return f"TTS generation response: {json.dumps(result)}"

        except requests.exceptions.ConnectionError:
            return "Text-to-speech service is not available. Ensure the n8n tts-generate workflow is active and the TTS server is running."
        except Exception as e:
            return f"Error generating speech: {str(e)}"
