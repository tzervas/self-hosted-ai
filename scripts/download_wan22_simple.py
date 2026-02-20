#!/usr/bin/env python3
"""
Download Wan2.2 FP8 video models from Kijai's pre-quantized repository.

This script uses the HuggingFace CLI to download pre-quantized FP8 models
optimized for 16GB VRAM GPUs. Requires HuggingFace authentication.

Setup:
    hf auth login  # Authenticate with your HuggingFace token

Usage:
    python3 scripts/download_wan22_simple.py
"""

import os
import subprocess
import sys
from pathlib import Path


def check_hf_auth():
    """Verify HuggingFace CLI is authenticated."""
    try:
        result = subprocess.run(
            ["hf", "auth", "whoami"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0 or "Not logged in" in result.stdout:
            print("❌ Not authenticated with HuggingFace")
            print("\nPlease run: hf auth login")
            print("Get your token from: https://huggingface.co/settings/tokens")
            sys.exit(1)
        username = result.stdout.strip().split("user:")[1].strip().split("\n")[0]
        print(f"✓ Authenticated as: {username}\n")
    except FileNotFoundError:
        print("❌ HuggingFace CLI not installed")
        print("\nPlease run: uv tool install huggingface_hub")
        sys.exit(1)


def download_model(repo: str, filename: str, output_dir: Path) -> Path:
    """Download a model file using HuggingFace CLI."""
    output_path = output_dir / filename

    # Skip if already exists
    if output_path.exists():
        size_gb = output_path.stat().st_size / (1024**3)
        print(f"✓ Already exists: {filename} ({size_gb:.1f}GB)")
        return output_path

    print(f"Downloading: {filename}")
    print(f"  From: {repo}")
    print(f"  To: {output_dir}/")

    cmd = [
        "hf", "download",
        repo,
        filename,
        "--local-dir", str(output_dir)
    ]

    try:
        subprocess.run(cmd, check=True)
        size_gb = output_path.stat().st_size / (1024**3)
        print(f"✓ Downloaded: {filename} ({size_gb:.1f}GB)\n")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to download {filename}: {e}")
        sys.exit(1)


def main():
    # Output directories
    models_dir = Path("/data/models/diffusion_models")
    vae_dir = Path("/data/models/vae")

    models_dir.mkdir(parents=True, exist_ok=True)
    vae_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Wan2.2 FP8 Video Model Downloader")
    print("Pre-quantized models optimized for 16GB VRAM from Kijai's repository")
    print("=" * 70)
    print()

    # Check authentication
    check_hf_auth()

    # Check disk space
    stat = os.statvfs(models_dir)
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
    needed_gb = 29.4  # 14GB I2V + 14GB T2V + 1.4GB VAE

    print(f"Disk space check:")
    print(f"  Available: {free_gb:.1f}GB")
    print(f"  Needed: {needed_gb:.1f}GB")

    if free_gb < needed_gb + 10:
        print(f"\n⚠️  WARNING: Low disk space! Recommended: {needed_gb + 10:.1f}GB")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            sys.exit(1)
    print()

    # Download models
    repo_fp8 = "Kijai/WanVideo_comfy_fp8_scaled"
    repo_vae = "Kijai/WanVideo_comfy"

    print("Downloading FP8 models (14GB each, optimized for 16GB VRAM)...")
    print()

    # Image-to-Video (HIGH quality)
    i2v_path = download_model(
        repo_fp8,
        "I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors",
        models_dir
    )

    # Text-to-Video (HIGH quality)
    t2v_path = download_model(
        repo_fp8,
        "T2V/Wan2_2-T2V-A14B_HIGH_fp8_e4m3fn_scaled_KJ.safetensors",
        models_dir
    )

    # VAE (shared by both models)
    vae_path = download_model(
        repo_vae,
        "Wan2_2_VAE_bf16.safetensors",
        vae_dir
    )

    print("\n" + "=" * 70)
    print("✅ Download complete!")
    print("=" * 70)
    print("\nModel locations:")
    print(f"  I2V: {i2v_path}")
    print(f"  T2V: {t2v_path}")
    print(f"  VAE: {vae_path}")
    print("\nModel details:")
    print("  - FP8 E4M3 quantization (14GB each vs 28GB FP16)")
    print("  - Optimized for 16GB VRAM with --lowvram flags")
    print("  - ComfyUI will detect on next restart")
    print("\nNext steps:")
    print("  1. Restart ComfyUI: kubectl rollout restart deployment/comfyui -n gpu-workloads")
    print("  2. Check logs: kubectl logs -n gpu-workloads deployment/comfyui --tail=100")
    print("  3. Test video generation workflows in ComfyUI web UI")


if __name__ == "__main__":
    main()
