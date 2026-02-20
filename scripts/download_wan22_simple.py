#!/usr/bin/env python3
"""Simple Wan2.2 model downloader without dependencies."""

import os
import sys
from pathlib import Path

def download_with_wget(url: str, output_path: Path):
    """Download using wget (always available)."""
    import subprocess

    print(f"Downloading {output_path.name}...")
    print(f"From: {url}")
    print(f"To: {output_path}")

    cmd = ["wget", "-c", "-O", str(output_path), url]
    subprocess.run(cmd, check=True)

    file_size_gb = output_path.stat().st_size / (1024**3)
    print(f"Downloaded: {file_size_gb:.2f}GB")

def main():
    # Output directories
    models_dir = Path("/data/models/diffusion_models")
    vae_dir = Path("/data/models/vae")

    models_dir.mkdir(parents=True, exist_ok=True)
    vae_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Wan2.2-I2V Model Downloader (Simplified)")
    print("=" * 60)

    # Direct HuggingFace URLs (from browser "Download" links)
    # These are the actual CDN URLs that don't require huggingface-cli
    base_url = "https://huggingface.co/ali-vilab/Wan2.2-I2V-A14B/resolve/main"

    downloads = [
        {
            "url": f"{base_url}/transformer/diffusion_pytorch_model.safetensors",
            "path": models_dir / "wan2.2-i2v-a14b.safetensors",
            "size_gb": 28
        },
        {
            "url": f"{base_url}/vae/diffusion_pytorch_model.safetensors",
            "path": vae_dir / "wan_2.2_vae.safetensors",
            "size_gb": 0.34
        }
    ]

    # Check disk space
    stat = os.statvfs(models_dir)
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
    total_needed = sum(d["size_gb"] for d in downloads)

    print(f"\nDisk space check:")
    print(f"  Available: {free_gb:.1f}GB")
    print(f"  Needed: {total_needed:.1f}GB")

    if free_gb < total_needed + 10:  # 10GB buffer
        print(f"\n⚠️  WARNING: Low disk space! Recommended: {total_needed + 10:.1f}GB")
        if input("Continue anyway? (yes/no): ").lower() != 'yes':
            sys.exit(1)

    # Download files
    for download in downloads:
        if download["path"].exists():
            print(f"\n✓ Already exists: {download['path'].name}")
            continue

        try:
            download_with_wget(download["url"], download["path"])
            print(f"✓ Downloaded: {download['path'].name}\n")
        except Exception as e:
            print(f"✗ Failed to download {download['path'].name}: {e}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Download complete!")
    print("=" * 60)
    print(f"\nModel location:")
    print(f"  Main model: {models_dir}/wan2.2-i2v-a14b.safetensors")
    print(f"  VAE: {vae_dir}/wan_2.2_vae.safetensors")
    print(f"\nNote: This is the FP16 version (28GB).")
    print(f"For FP8 quantization, install optimum-quanto and run the original script.")
    print(f"\nComfyUI will detect these models on next restart.")

if __name__ == "__main__":
    main()
