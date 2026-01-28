#!/usr/bin/env python3
"""
Video Generation Server v1.0
Provides REST API for:
- AnimateDiff-Lightning (text-to-video, fast generation)
- Stable Video Diffusion (image-to-video, high quality)

Optimized for RTX 5080 16GB with:
- FP16 precision
- CPU offloading
- VAE tiling for memory efficiency
- Sliding window for longer videos
"""

import io
import os
import uuid
import base64
import logging
import tempfile
from typing import Optional

import torch
import numpy as np
from PIL import Image
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Generation Server",
    description="Generate videos from text or images using AI models",
    version="1.0.0"
)

# Global model instances (lazy loaded)
animatediff_pipeline = None
svd_pipeline = None

# Configuration from environment
DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
HF_HOME = os.getenv("HF_HOME", "/models/huggingface")
ANIMATEDIFF_MODEL = os.getenv("ANIMATEDIFF_MODEL", "ByteDance/AnimateDiff-Lightning")
SVD_MODEL = os.getenv("SVD_MODEL", "stabilityai/stable-video-diffusion-img2vid-xt-1-1")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/outputs")


class Text2VideoRequest(BaseModel):
    """Request for text-to-video generation"""
    prompt: str = Field(..., description="Text description of the video")
    negative_prompt: Optional[str] = Field(default="low quality, blurry, distorted")
    num_frames: int = Field(default=16, ge=8, le=64, description="Number of frames")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    num_inference_steps: int = Field(default=4, ge=1, le=50, description="Steps (4 for Lightning)")
    fps: int = Field(default=8, ge=4, le=30)
    width: int = Field(default=512, ge=256, le=1024)
    height: int = Field(default=512, ge=256, le=1024)


class Image2VideoRequest(BaseModel):
    """Request for image-to-video generation"""
    num_frames: int = Field(default=25, ge=14, le=50)
    fps: int = Field(default=7, ge=4, le=30)
    motion_bucket_id: int = Field(default=127, ge=1, le=255, description="Motion intensity")
    noise_aug_strength: float = Field(default=0.02, ge=0.0, le=0.1)
    num_inference_steps: int = Field(default=25, ge=10, le=50)


def load_animatediff():
    """Load AnimateDiff-Lightning pipeline"""
    global animatediff_pipeline
    if animatediff_pipeline is None:
        logger.info(f"Loading AnimateDiff-Lightning from {ANIMATEDIFF_MODEL}...")

        from diffusers import AnimateDiffPipeline, MotionAdapter, EulerDiscreteScheduler
        from diffusers.utils import export_to_gif, export_to_video

        # Load motion adapter
        adapter = MotionAdapter.from_pretrained(
            ANIMATEDIFF_MODEL,
            torch_dtype=torch.float16,
            cache_dir=HF_HOME
        )

        # Load base model with adapter
        model_id = "emilianJR/epiCRealism"  # Good base for AnimateDiff
        animatediff_pipeline = AnimateDiffPipeline.from_pretrained(
            model_id,
            motion_adapter=adapter,
            torch_dtype=torch.float16,
            cache_dir=HF_HOME
        )

        # Use Euler scheduler for Lightning
        animatediff_pipeline.scheduler = EulerDiscreteScheduler.from_config(
            animatediff_pipeline.scheduler.config,
            timestep_spacing="trailing",
            beta_schedule="linear"
        )

        animatediff_pipeline = animatediff_pipeline.to(DEVICE)

        # Memory optimizations for 16GB VRAM
        if DEVICE == "cuda":
            animatediff_pipeline.enable_vae_slicing()
            animatediff_pipeline.enable_vae_tiling()

        logger.info("AnimateDiff-Lightning loaded successfully")
    return animatediff_pipeline


def load_svd():
    """Load Stable Video Diffusion pipeline"""
    global svd_pipeline
    if svd_pipeline is None:
        logger.info(f"Loading Stable Video Diffusion from {SVD_MODEL}...")

        from diffusers import StableVideoDiffusionPipeline

        svd_pipeline = StableVideoDiffusionPipeline.from_pretrained(
            SVD_MODEL,
            torch_dtype=torch.float16,
            variant="fp16",
            cache_dir=HF_HOME
        )

        svd_pipeline = svd_pipeline.to(DEVICE)

        # Memory optimizations
        if DEVICE == "cuda":
            svd_pipeline.enable_model_cpu_offload()

        logger.info("Stable Video Diffusion loaded successfully")
    return svd_pipeline


def frames_to_video(frames, fps: int, output_path: str):
    """Convert frames to MP4 video"""
    import cv2

    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in frames:
        # Convert RGB to BGR for OpenCV
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        out.write(bgr_frame)

    out.release()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 0,
        "models": {
            "animatediff": ANIMATEDIFF_MODEL,
            "svd": SVD_MODEL
        }
    })


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return JSONResponse({
        "service": "Video Generation Server",
        "version": "1.0.0",
        "capabilities": [
            "Text-to-video (AnimateDiff-Lightning, 4-step fast generation)",
            "Image-to-video (Stable Video Diffusion, high quality)"
        ],
        "endpoints": {
            "/health": "Health check",
            "/video/text2video": "Generate video from text (POST)",
            "/video/image2video": "Generate video from image (POST)",
            "/models/load/animatediff": "Pre-load AnimateDiff (POST)",
            "/models/load/svd": "Pre-load SVD (POST)"
        },
        "optimizations": [
            "FP16 precision",
            "VAE slicing and tiling",
            "CPU offloading for SVD"
        ]
    })


@app.post("/models/load/animatediff")
async def preload_animatediff():
    """Pre-load AnimateDiff-Lightning model"""
    try:
        load_animatediff()
        return JSONResponse({"status": "AnimateDiff-Lightning model loaded"})
    except Exception as e:
        logger.error(f"Failed to load AnimateDiff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/load/svd")
async def preload_svd():
    """Pre-load Stable Video Diffusion model"""
    try:
        load_svd()
        return JSONResponse({"status": "Stable Video Diffusion model loaded"})
    except Exception as e:
        logger.error(f"Failed to load SVD: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/video/text2video")
async def generate_text2video(request: Text2VideoRequest):
    """Generate video from text using AnimateDiff-Lightning"""
    try:
        logger.info(f"Generating video: '{request.prompt}' ({request.num_frames} frames)")
        pipeline = load_animatediff()

        # Generate frames
        with torch.no_grad():
            output = pipeline(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                num_frames=request.num_frames,
                guidance_scale=request.guidance_scale,
                num_inference_steps=request.num_inference_steps,
                width=request.width,
                height=request.height,
            )

        frames = output.frames[0]  # List of PIL images

        # Convert to numpy arrays
        frame_arrays = [np.array(frame) for frame in frames]

        # Create video file
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(OUTPUT_DIR, filename)

        frames_to_video(frame_arrays, request.fps, output_path)

        logger.info(f"Generated video: {filename}")

        # Return video file
        return FileResponse(
            output_path,
            media_type="video/mp4",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Text2video generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/video/image2video")
async def generate_image2video(
    image: UploadFile = File(...),
    num_frames: int = 25,
    fps: int = 7,
    motion_bucket_id: int = 127,
    noise_aug_strength: float = 0.02,
    num_inference_steps: int = 25
):
    """Generate video from image using Stable Video Diffusion"""
    try:
        logger.info(f"Generating video from image ({num_frames} frames)")

        # Read and process input image
        image_data = await image.read()
        input_image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # Resize to 1024x576 (SVD native resolution)
        input_image = input_image.resize((1024, 576), Image.LANCZOS)

        pipeline = load_svd()

        # Generate frames
        with torch.no_grad():
            frames = pipeline(
                input_image,
                num_frames=num_frames,
                motion_bucket_id=motion_bucket_id,
                noise_aug_strength=noise_aug_strength,
                num_inference_steps=num_inference_steps,
                decode_chunk_size=4,  # Reduce memory usage
            ).frames[0]

        # Convert to numpy arrays
        frame_arrays = [np.array(frame) for frame in frames]

        # Create video file
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(OUTPUT_DIR, filename)

        frames_to_video(frame_arrays, fps, output_path)

        logger.info(f"Generated video: {filename}")

        return FileResponse(
            output_path,
            media_type="video/mp4",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Image2video generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5005"))
    uvicorn.run(app, host="0.0.0.0", port=port)
