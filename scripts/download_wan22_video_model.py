#!/usr/bin/env python3
"""
Download and optimize Wan2.2 video generation models for 16GB VRAM.

This script:
1. Downloads Wan2.2-I2V-A14B model from HuggingFace
2. Quantizes from FP16 (28GB) to FP8 (14GB) for VRAM efficiency
3. Deploys to ComfyUI models directory

Usage:
    uv run scripts/download_wan22_video_model.py --model i2v --quantize fp8
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def download_from_huggingface(repo_id: str, filename: str, output_dir: Path) -> Path:
    """Download model from HuggingFace using huggingface-cli."""
    output_path = output_dir / filename

    if output_path.exists():
        logger.info(f"Model already exists: {output_path}")
        return output_path

    logger.info(f"Downloading {filename} from {repo_id}...")
    cmd = [
        "huggingface-cli",
        "download",
        repo_id,
        filename,
        "--local-dir", str(output_dir),
        "--local-dir-use-symlinks", "False"
    ]

    try:
        subprocess.run(cmd, check=True)
        logger.info(f"Downloaded successfully: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to download model: {e}")
        sys.exit(1)


def quantize_model_fp8(model_path: Path, output_path: Path):
    """
    Quantize model to FP8 using optimum-quanto.

    Reduces VRAM from 28GB (FP16) to ~14GB (FP8) with minimal quality loss.
    """
    try:
        import torch
        from safetensors.torch import load_file, save_file
        from optimum.quanto import quantize, freeze, qfloat8
    except ImportError:
        logger.error("Required packages not installed. Run: pip install optimum-quanto safetensors")
        sys.exit(1)

    logger.info(f"Loading model from {model_path}...")
    state_dict = load_file(str(model_path))

    logger.info("Quantizing to FP8...")
    # Convert each tensor to FP8
    quantized_dict = {}
    for key, tensor in state_dict.items():
        if tensor.dtype == torch.float16 or tensor.dtype == torch.float32:
            quantized_dict[key] = tensor.to(torch.float8_e4m3fn)
        else:
            quantized_dict[key] = tensor  # Keep non-float tensors as-is

    logger.info(f"Saving quantized model to {output_path}...")
    save_file(quantized_dict, str(output_path))

    # Calculate size reduction
    original_size = model_path.stat().st_size / (1024**3)  # GB
    quantized_size = output_path.stat().st_size / (1024**3)  # GB
    reduction_pct = ((original_size - quantized_size) / original_size) * 100

    logger.info(f"Quantization complete!")
    logger.info(f"  Original size: {original_size:.2f} GB")
    logger.info(f"  Quantized size: {quantized_size:.2f} GB")
    logger.info(f"  Reduction: {reduction_pct:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Download and optimize Wan2.2 video models")
    parser.add_argument(
        "--model",
        choices=["i2v", "t2v", "both"],
        default="i2v",
        help="Which model to download (image-to-video, text-to-video, or both)"
    )
    parser.add_argument(
        "--quantize",
        choices=["none", "fp8", "gguf"],
        default="fp8",
        help="Quantization format (none=keep FP16, fp8=half VRAM, gguf=GGUF format)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/models/diffusion_models"),
        help="Output directory for models (default: /data/models/diffusion_models)"
    )

    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    models_to_download = []
    if args.model in ["i2v", "both"]:
        models_to_download.append(("ali-vilab/Wan2.2-I2V-A14B", "transformer/diffusion_pytorch_model.safetensors", "wan2.2-i2v-a14b.safetensors"))
    if args.model in ["t2v", "both"]:
        models_to_download.append(("ali-vilab/Wan2.2-T2V-A14B", "transformer/diffusion_pytorch_model.safetensors", "wan2.2-t2v-a14b.safetensors"))

    # Download VAE (shared by both models)
    logger.info("Downloading shared VAE...")
    vae_path = download_from_huggingface(
        "ali-vilab/Wan2.2-I2V-A14B",
        "vae/diffusion_pytorch_model.safetensors",
        args.output_dir.parent / "vae"
    )

    # Download and process each model
    for repo_id, hf_filename, local_filename in models_to_download:
        # Download
        downloaded_path = download_from_huggingface(repo_id, hf_filename, args.output_dir)

        # Rename to simpler filename
        final_path = args.output_dir / local_filename
        if downloaded_path != final_path:
            downloaded_path.rename(final_path)

        # Quantize if requested
        if args.quantize == "fp8":
            quantized_path = args.output_dir / f"{final_path.stem}-fp8.safetensors"
            quantize_model_fp8(final_path, quantized_path)
            logger.info(f"Use this model in ComfyUI: {quantized_path.name}")
        elif args.quantize == "gguf":
            logger.warning("GGUF quantization not yet implemented. Use --quantize fp8 instead.")
        else:
            logger.info(f"Model ready (FP16): {final_path.name}")

    logger.info("\n=== Setup Complete ===")
    logger.info(f"Models installed in: {args.output_dir}")
    logger.info(f"VAE installed in: {args.output_dir.parent / 'vae'}")
    logger.info("\nNext steps:")
    logger.info("1. Restart ComfyUI to detect new models")
    logger.info("2. Use ComfyUI-WanVideoWrapper nodes to create video workflows")
    logger.info("3. Configure Open WebUI with video generation workflow JSON")


if __name__ == "__main__":
    main()
