#!/usr/bin/env python3
"""
Download models for GlitchHunter.

Downloads quantized GGUF models from HuggingFace for use with llama-cpp-python.
Supports multiple model sizes for different hardware stacks.

Usage:
    python scripts/download_models.py [--stack-a|--stack-b|--all]
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# HuggingFace download helper
try:
    from huggingface_hub import hf_hub_download
    HAS_HF = True
except ImportError:
    HAS_HF = False
    print("Warning: huggingface_hub not installed. Using manual download URLs.")
    print("Install with: pip install huggingface_hub")


# Model definitions
MODELS: Dict[str, Dict[str, str]] = {
    # Stack A models (GTX 3060, 8GB VRAM)
    "qwen3.5-9b": {
        "repo_id": "Qwen/Qwen3.5-9B-Instruct-GGUF",
        "filename": "qwen3.5-9b-instruct-q4_k_m.gguf",
        "description": "Qwen3.5 9B Instruct (Q4_K_M quantization)",
        "size_gb": 5.5,
        "stack": "stack_a",
    },
    "phi-4-mini": {
        "repo_id": "microsoft/phi-4-mini-instruct-gguf",
        "filename": "phi-4-mini-instruct-q4_k_m.gguf",
        "description": "Phi-4-mini Instruct (Q4_K_M quantization)",
        "size_gb": 2.5,
        "stack": "stack_a",
    },
    
    # Stack B models (RTX 3090, 24GB VRAM)
    "qwen3.5-27b": {
        "repo_id": "Qwen/Qwen3.5-27B-Instruct-GGUF",
        "filename": "qwen3.5-27b-instruct-q4_k_m.gguf",
        "description": "Qwen3.5 27B Instruct (Q4_K_M quantization)",
        "size_gb": 16.0,
        "stack": "stack_b",
    },
    "deepseek-v3.2-small": {
        "repo_id": "deepseek-ai/DeepSeek-V3.2-Small-GGUF",
        "filename": "deepseek-v3.2-small-q4_k_m.gguf",
        "description": "DeepSeek-V3.2 Small (Q4_K_M quantization)",
        "size_gb": 8.0,
        "stack": "stack_b",
    },
    
    # Embedding model (both stacks)
    "nomic-embed-text": {
        "repo_id": "nomic-ai/nomic-embed-text-v1.5-GGUF",
        "filename": "nomic-embed-text-v1.5.f16.gguf",
        "description": "Nomic Embed Text v1.5",
        "size_gb": 0.5,
        "stack": "both",
    },
}


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def download_model(
    model_key: str,
    output_dir: Path,
    force: bool = False,
) -> Optional[Path]:
    """
    Download a model from HuggingFace.

    Args:
        model_key: Key from MODELS dictionary
        output_dir: Directory to save model
        force: Force re-download

    Returns:
        Path to downloaded model or None
    """
    if model_key not in MODELS:
        print(f"Error: Unknown model '{model_key}'")
        return None

    model_info = MODELS[model_key]
    output_path = output_dir / model_info["filename"]

    # Check if already exists
    if output_path.exists() and not force:
        print(f"✓ {model_info['description']} already exists")
        print(f"  Path: {output_path}")
        return output_path

    print(f"\nDownloading: {model_info['description']}")
    print(f"  Size: ~{model_info['size_gb']} GB")
    print(f"  Stack: {model_info['stack']}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    if HAS_HF:
        try:
            # Download using huggingface_hub
            downloaded_path = hf_hub_download(
                repo_id=model_info["repo_id"],
                filename=model_info["filename"],
                local_dir=str(output_dir),
                force_download=force,
            )
            print(f"✓ Downloaded to: {downloaded_path}")
            return Path(downloaded_path)

        except Exception as e:
            print(f"Error downloading with huggingface_hub: {e}")
            print("Falling back to manual download...")

    # Manual download instructions
    print("\n" + "=" * 60)
    print("Manual download required:")
    print("=" * 60)
    print(f"1. Visit: https://huggingface.co/{model_info['repo_id']}")
    print(f"2. Download: {model_info['filename']}")
    print(f"3. Save to: {output_path}")
    print("=" * 60 + "\n")

    return None


def download_stack(
    stack: str,
    output_dir: Path,
    force: bool = False,
) -> List[Path]:
    """
    Download all models for a hardware stack.

    Args:
        stack: Stack name ('stack_a', 'stack_b', or 'both')
        output_dir: Directory to save models
        force: Force re-download

    Returns:
        List of downloaded model paths
    """
    downloaded = []

    for model_key, model_info in MODELS.items():
        if model_info["stack"] == stack or model_info["stack"] == "both":
            path = download_model(model_key, output_dir, force)
            if path:
                downloaded.append(path)

    return downloaded


def list_models() -> None:
    """List all available models."""
    print("\nAvailable Models:")
    print("=" * 70)

    for stack in ["stack_a", "stack_b", "both"]:
        print(f"\n{stack.upper()}:")
        for model_key, model_info in MODELS.items():
            if model_info["stack"] == stack:
                print(f"  {model_key}")
                print(f"    Description: {model_info['description']}")
                print(f"    Size: ~{model_info['size_gb']} GB")
                print(f"    Repo: {model_info['repo_id']}")
                print(f"    File: {model_info['filename']}")

    print("\n" + "=" * 70)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download models for GlitchHunter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --stack-a          Download Stack A models (GTX 3060)
  %(prog)s --stack-b          Download Stack B models (RTX 3090)
  %(prog)s --all              Download all models
  %(prog)s --list             List available models
  %(prog)s qwen3.5-9b         Download specific model
        """,
    )

    parser.add_argument(
        "--stack-a",
        action="store_true",
        help="Download Stack A models (GTX 3060, 8GB)",
    )
    parser.add_argument(
        "--stack-b",
        action="store_true",
        help="Download Stack B models (RTX 3090, 24GB)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all models",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available models",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download existing models",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models"),
        help="Output directory for models (default: models)",
    )
    parser.add_argument(
        "model",
        nargs="?",
        help="Download specific model by key",
    )

    args = parser.parse_args()

    # Determine output directory
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # List models
    if args.list:
        list_models()
        return 0

    # Download requested models
    downloaded = []

    if args.stack_a:
        print("\n=== Downloading Stack A models ===")
        downloaded.extend(download_stack("stack_a", output_dir, args.force))

    if args.stack_b:
        print("\n=== Downloading Stack B models ===")
        downloaded.extend(download_stack("stack_b", output_dir, args.force))

    if args.all:
        print("\n=== Downloading all models ===")
        downloaded.extend(download_stack("stack_a", output_dir, args.force))
        downloaded.extend(download_stack("stack_b", output_dir, args.force))

    if args.model:
        print(f"\n=== Downloading {args.model} ===")
        path = download_model(args.model, output_dir, args.force)
        if path:
            downloaded.append(path)

    # Summary
    print("\n" + "=" * 60)
    print("Download Summary:")
    print("=" * 60)
    print(f"Downloaded: {len(downloaded)} model(s)")
    for path in downloaded:
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  ✓ {path.name} ({size_mb:.1f} MB)")
    print("=" * 60)

    if not downloaded:
        print("\nNo models downloaded. Use --help for usage information.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
