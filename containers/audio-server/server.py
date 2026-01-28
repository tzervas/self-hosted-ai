#!/usr/bin/env python3
"""
Audio Generation Server v1.1
Provides REST API for:
- AudioLDM2 (high-quality sound effects)
- MusicGen (music generation)
- Bark (high-quality voice/speech with emotion and multilingual support)
"""

import io
import os
import uuid
import logging
from typing import Optional, List

import torch
import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Audio Generation Server",
    description="Generate high-quality sound effects, music, and voice using AI models",
    version="1.1.0"
)

# Global model instances (lazy loaded)
audioldm_pipeline = None
musicgen_model = None
musicgen_processor = None
bark_model = None
bark_processor = None

# Configuration from environment
DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
HF_HOME = os.getenv("HF_HOME", "/models/huggingface")
AUDIOLDM_MODEL = os.getenv("AUDIOLDM_MODEL", "cvssp/audioldm2-large")
MUSICGEN_MODEL = os.getenv("MUSICGEN_MODEL", "facebook/musicgen-large")
BARK_MODEL = os.getenv("BARK_MODEL", "suno/bark")


class AudioRequest(BaseModel):
    """Request for sound effect generation"""
    prompt: str = Field(..., description="Text description of the sound effect")
    duration: float = Field(default=5.0, ge=1.0, le=30.0, description="Duration in seconds")
    guidance_scale: float = Field(default=3.5, ge=1.0, le=15.0)
    num_inference_steps: int = Field(default=50, ge=10, le=200)
    negative_prompt: Optional[str] = Field(default=None)


class MusicRequest(BaseModel):
    """Request for music generation"""
    prompt: str = Field(..., description="Text description of the music")
    duration: float = Field(default=10.0, ge=1.0, le=60.0, description="Duration in seconds")
    temperature: float = Field(default=1.0, ge=0.1, le=2.0)
    top_k: int = Field(default=250, ge=1, le=1000)
    top_p: float = Field(default=0.0, ge=0.0, le=1.0)


class VoiceRequest(BaseModel):
    """Request for voice/speech generation with Bark"""
    text: str = Field(..., description="Text to convert to speech")
    voice_preset: Optional[str] = Field(
        default=None,
        description="Voice preset (e.g., 'v2/en_speaker_6' for English male)"
    )
    temperature: float = Field(default=0.7, ge=0.1, le=1.5)
    fine_temperature: float = Field(default=0.5, ge=0.1, le=1.5)


def load_audioldm():
    """Load AudioLDM2 model"""
    global audioldm_pipeline
    if audioldm_pipeline is None:
        logger.info(f"Loading AudioLDM2 model from {AUDIOLDM_MODEL}...")
        from diffusers import AudioLDM2Pipeline
        audioldm_pipeline = AudioLDM2Pipeline.from_pretrained(
            AUDIOLDM_MODEL,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            cache_dir=HF_HOME
        )
        audioldm_pipeline = audioldm_pipeline.to(DEVICE)
        if DEVICE == "cuda":
            audioldm_pipeline.enable_model_cpu_offload()
        logger.info("AudioLDM2 model loaded successfully")
    return audioldm_pipeline


def load_musicgen():
    """Load MusicGen model"""
    global musicgen_model, musicgen_processor
    if musicgen_model is None:
        logger.info(f"Loading MusicGen model from {MUSICGEN_MODEL}...")
        from transformers import AutoProcessor, MusicgenForConditionalGeneration
        musicgen_processor = AutoProcessor.from_pretrained(
            MUSICGEN_MODEL,
            cache_dir=HF_HOME
        )
        musicgen_model = MusicgenForConditionalGeneration.from_pretrained(
            MUSICGEN_MODEL,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            cache_dir=HF_HOME
        )
        musicgen_model = musicgen_model.to(DEVICE)
        logger.info("MusicGen model loaded successfully")
    return musicgen_model, musicgen_processor


def load_bark():
    """Load Bark model for voice generation"""
    global bark_model, bark_processor
    if bark_model is None:
        logger.info(f"Loading Bark model from {BARK_MODEL}...")
        from transformers import AutoProcessor, BarkModel
        bark_processor = AutoProcessor.from_pretrained(
            BARK_MODEL,
            cache_dir=HF_HOME
        )
        bark_model = BarkModel.from_pretrained(
            BARK_MODEL,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            cache_dir=HF_HOME
        )
        bark_model = bark_model.to(DEVICE)
        if DEVICE == "cuda":
            bark_model.enable_cpu_offload()
        logger.info("Bark model loaded successfully")
    return bark_model, bark_processor


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "models": {
            "audioldm": AUDIOLDM_MODEL,
            "musicgen": MUSICGEN_MODEL,
            "bark": BARK_MODEL
        }
    })


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return JSONResponse({
        "service": "Audio Generation Server",
        "version": "1.1.0",
        "capabilities": [
            "High-quality sound effects (AudioLDM2)",
            "Music generation (MusicGen)",
            "Voice synthesis with emotion (Bark)"
        ],
        "endpoints": {
            "/health": "Health check",
            "/audio/generate": "Generate sound effects (POST)",
            "/music/generate": "Generate music (POST)",
            "/voice/generate": "Generate speech/voice (POST)",
            "/voice/presets": "List available voice presets (GET)",
            "/models/load/audioldm": "Pre-load AudioLDM2 (POST)",
            "/models/load/musicgen": "Pre-load MusicGen (POST)",
            "/models/load/bark": "Pre-load Bark (POST)"
        }
    })


@app.get("/voice/presets")
async def list_voice_presets():
    """List available Bark voice presets"""
    presets = {
        "english": [
            "v2/en_speaker_0", "v2/en_speaker_1", "v2/en_speaker_2",
            "v2/en_speaker_3", "v2/en_speaker_4", "v2/en_speaker_5",
            "v2/en_speaker_6", "v2/en_speaker_7", "v2/en_speaker_8",
            "v2/en_speaker_9"
        ],
        "multilingual": [
            "v2/de_speaker_0", "v2/de_speaker_1", "v2/de_speaker_2",  # German
            "v2/es_speaker_0", "v2/es_speaker_1", "v2/es_speaker_2",  # Spanish
            "v2/fr_speaker_0", "v2/fr_speaker_1", "v2/fr_speaker_2",  # French
            "v2/it_speaker_0", "v2/it_speaker_1", "v2/it_speaker_2",  # Italian
            "v2/ja_speaker_0", "v2/ja_speaker_1", "v2/ja_speaker_2",  # Japanese
            "v2/ko_speaker_0", "v2/ko_speaker_1", "v2/ko_speaker_2",  # Korean
            "v2/pl_speaker_0", "v2/pl_speaker_1", "v2/pl_speaker_2",  # Polish
            "v2/pt_speaker_0", "v2/pt_speaker_1", "v2/pt_speaker_2",  # Portuguese
            "v2/ru_speaker_0", "v2/ru_speaker_1", "v2/ru_speaker_2",  # Russian
            "v2/tr_speaker_0", "v2/tr_speaker_1", "v2/tr_speaker_2",  # Turkish
            "v2/zh_speaker_0", "v2/zh_speaker_1", "v2/zh_speaker_2",  # Chinese
        ],
        "tips": [
            "Use [laughter] for laughing",
            "Use [sighs] for sighing",
            "Use [music] for singing/music",
            "Use [gasps] for gasping",
            "Use ... for hesitation",
            "Use CAPS for emphasis",
            "Use ♪ for singing"
        ]
    }
    return JSONResponse(presets)


@app.post("/models/load/audioldm")
async def preload_audioldm():
    """Pre-load AudioLDM2 model"""
    try:
        load_audioldm()
        return JSONResponse({"status": "AudioLDM2 model loaded"})
    except Exception as e:
        logger.error(f"Failed to load AudioLDM2: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/load/musicgen")
async def preload_musicgen():
    """Pre-load MusicGen model"""
    try:
        load_musicgen()
        return JSONResponse({"status": "MusicGen model loaded"})
    except Exception as e:
        logger.error(f"Failed to load MusicGen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/load/bark")
async def preload_bark():
    """Pre-load Bark model"""
    try:
        load_bark()
        return JSONResponse({"status": "Bark model loaded"})
    except Exception as e:
        logger.error(f"Failed to load Bark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audio/generate")
async def generate_audio(request: AudioRequest):
    """Generate high-quality sound effects using AudioLDM2"""
    try:
        logger.info(f"Generating SFX: '{request.prompt}' ({request.duration}s)")
        pipeline = load_audioldm()

        # Generate audio
        audio = pipeline(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            audio_length_in_s=request.duration,
        ).audios[0]

        # Convert to WAV
        buffer = io.BytesIO()
        sf.write(buffer, audio, samplerate=16000, format='WAV')
        buffer.seek(0)

        filename = f"sfx_{uuid.uuid4().hex[:8]}.wav"
        logger.info(f"Generated SFX: {filename}")

        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"SFX generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/music/generate")
async def generate_music(request: MusicRequest):
    """Generate music using MusicGen"""
    try:
        logger.info(f"Generating music: '{request.prompt}' ({request.duration}s)")
        model, processor = load_musicgen()

        # Prepare inputs
        inputs = processor(
            text=[request.prompt],
            padding=True,
            return_tensors="pt"
        ).to(DEVICE)

        # Calculate max new tokens based on duration (50 tokens/second at 32kHz)
        max_new_tokens = int(request.duration * 50)

        # Generate music
        with torch.no_grad():
            audio_values = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=request.temperature,
                top_k=request.top_k if request.top_k > 0 else None,
                top_p=request.top_p if request.top_p > 0 else None,
            )

        # Convert to numpy
        audio = audio_values[0, 0].cpu().numpy()

        # Convert to WAV
        buffer = io.BytesIO()
        sf.write(buffer, audio, samplerate=model.config.audio_encoder.sampling_rate, format='WAV')
        buffer.seek(0)

        filename = f"music_{uuid.uuid4().hex[:8]}.wav"
        logger.info(f"Generated music: {filename}")

        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Music generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/generate")
async def generate_voice(request: VoiceRequest):
    """Generate high-quality speech using Bark with emotion support"""
    try:
        logger.info(f"Generating voice: '{request.text[:50]}...'")
        model, processor = load_bark()

        # Prepare inputs
        inputs = processor(
            request.text,
            voice_preset=request.voice_preset,
            return_tensors="pt"
        ).to(DEVICE)

        # Generate speech
        with torch.no_grad():
            audio_array = model.generate(
                **inputs,
                semantic_temperature=request.temperature,
                fine_temperature=request.fine_temperature,
            )

        # Convert to numpy
        audio = audio_array.cpu().numpy().squeeze()

        # Bark sample rate is 24kHz
        sample_rate = model.generation_config.sample_rate

        # Convert to WAV
        buffer = io.BytesIO()
        sf.write(buffer, audio, samplerate=sample_rate, format='WAV')
        buffer.seek(0)

        filename = f"voice_{uuid.uuid4().hex[:8]}.wav"
        logger.info(f"Generated voice: {filename}")

        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Voice generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
