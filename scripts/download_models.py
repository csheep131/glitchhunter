#!/usr/bin/env python3
"""
Download models for GlitchHunter.

Downloads quantized GGUF models from HuggingFace for use with llama-cpp-python.
Supports multiple model sizes for different hardware stacks.

Uses model configuration from config.yaml to determine what models to download.

Usage:
    python scripts/download_models.py [--stack-a|--stack-b|--all]
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add src to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# HuggingFace download helper
try:
    from huggingface_hub import hf_hub_download
    HAS_HF = True
except ImportError:
    HAS_HF = False
    print("Warning: huggingface_hub not installed. Using manual download URLs.")
    print("Install with: pip install huggingface_hub")


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def load_config_models(config_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """
    Load model configurations from config.yaml.
    
    Args:
        config_path: Path to config.yaml (default: project root config.yaml)
    
    Returns:
        Dictionary of model configurations
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"
    
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return {}
    
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        model_downloads = config_data.get("model_downloads", {})
        print(f"Loaded {len(model_downloads)} model configurations from {config_path}")
        return model_downloads
    
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        print("Falling back to hardcoded model configurations...")
        return get_fallback_models()


def get_fallback_models() -> Dict[str, Dict[str, Any]]:
    """Fallback model definitions if config loading fails."""
    return {
        # Stack A models (GTX 3060, 8GB VRAM)
        "qwen3.5-9b": {
            "repo_id": "Qwen/Qwen3.5-9B-Instruct-GGUF",
            "filename": "qwen3.5-9b-instruct-q4_k_m.gguf",
            "description": "Qwen3.5 9B Instruct (Q4_K_M quantization)",
            "size_gb": 5.5,
            "stack": "stack_a",
        },
        "phi-4-mini": {
            "repo_id": "bartowski/microsoft_Phi-4-mini-instruct-GGUF",
            "filename": "Phi-4-mini-instruct-Q4_K_M.gguf",
            "description": "Phi-4-mini Instruct by bartowski (Q4_K_M quantization)",
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


def download_model(
    model_key: str,
    model_info: Dict[str, Any],
    output_dir: Path,
    force: bool = False,
) -> Optional[Path]:
    """
    Download a model from HuggingFace.
    
    Args:
        model_key: Key identifying the model
        model_info: Model configuration dictionary
        output_dir: Directory to save model
        force: Force re-download
    
    Returns:
        Path to downloaded model or None
    """
    output_path = output_dir / model_info["filename"]
    
    # Check if already exists
    if output_path.exists() and not force:
        print(f"✓ {model_info.get('description', model_key)} already exists")
        print(f"  Path: {output_path}")
        return output_path
    
    description = model_info.get("description", model_key)
    size_gb = model_info.get("size_gb", "unknown")
    stack = model_info.get("stack", "unknown")
    
    print(f"\nDownloading: {description}")
    print(f"  Size: ~{size_gb} GB")
    print(f"  Stack: {stack}")
    
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
    models: Dict[str, Dict[str, Any]],
    output_dir: Path,
    force: bool = False,
) -> List[Path]:
    """
    Download all models for a hardware stack.
    
    Args:
        stack: Stack name ('stack_a', 'stack_b', or 'both')
        models: Dictionary of model configurations
        output_dir: Directory to save models
        force: Force re-download
    
    Returns:
        List of downloaded model paths
    """
    downloaded = []
    
    for model_key, model_info in models.items():
        model_stack = model_info.get("stack", "unknown")
        if model_stack == stack or model_stack == "both":
            path = download_model(model_key, model_info, output_dir, force)
            if path:
                downloaded.append(path)
    
    return downloaded


def list_models(models: Dict[str, Dict[str, Any]]) -> None:
    """List all available models."""
    print("\nAvailable Models:")
    print("=" * 70)
    
    # Group by stack
    stacks = {}
    for model_key, model_info in models.items():
        stack = model_info.get("stack", "unknown")
        if stack not in stacks:
            stacks[stack] = []
        stacks[stack].append((model_key, model_info))
    
    for stack in sorted(stacks.keys()):
        print(f"\n{stack.upper()}:")
        for model_key, model_info in stacks[stack]:
            print(f"  {model_key}")
            print(f"    Description: {model_info.get('description', 'N/A')}")
            print(f"    Size: ~{model_info.get('size_gb', 'unknown')} GB")
            print(f"    Repo: {model_info.get('repo_id', 'N/A')}")
            print(f"    File: {model_info.get('filename', 'N/A')}")
    
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
  %(prog)s --config path      Use custom config file
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
        default=Path.home() / "stuff" / "offline_llm" / "models",
        help="Output directory for models (default: ~/stuff/offline_llm/models)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml (default: config.yaml in project root)",
    )
    parser.add_argument(
        "model",
        nargs="?",
        help="Download specific model by key",
    )
    
    args = parser.parse_args()
    
    # Load model configurations
    models = load_config_models(args.config)
    if not models:
        print("No model configurations found. Exiting.")
        return 1
    
    # Determine output directory
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # List models
    if args.list:
        list_models(models)
        return 0
    
    # Download requested models
    downloaded = []
    
    if args.stack_a:
        print("\n=== Downloading Stack A models ===")
        downloaded.extend(download_stack("stack_a", models, output_dir, args.force))
    
    if args.stack_b:
        print("\n=== Downloading Stack B models ===")
        downloaded.extend(download_stack("stack_b", models, output_dir, args.force))
    
    if args.all:
        print("\n=== Downloading all models ===")
        # Download all stacks
        for stack in ["stack_a", "stack_b"]:
            downloaded.extend(download_stack(stack, models, output_dir, args.force))
        # Also download "both" stack models
        downloaded.extend(download_stack("both", models, output_dir, args.force))
    
    if args.model:
        print(f"\n=== Downloading {args.model} ===")
        if args.model in models:
            path = download_model(args.model, models[args.model], output_dir, args.force)
            if path:
                downloaded.append(path)
        else:
            print(f"Error: Unknown model '{args.model}'")
            print("Available models:")
            for key in models.keys():
                print(f"  - {key}")
            return 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Download Summary:")
    print("=" * 60)
    print(f"Downloaded: {len(downloaded)} model(s)")
    for path in downloaded:
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  ✓ {path.name} ({size_mb:.1f} MB)")
        else:
            print(f"  ⚠ {path.name} (manual download required)")
    print("=" * 60)
    
    if not downloaded:
        print("\nNo models downloaded. Use --help for usage information.")
        return 1
    
    # Verify model paths match hardware config
    print("\nVerifying model paths in hardware configuration...")
    try:
        from core.config import Config
        config = Config.load(args.config)
        
        for stack_name in ["stack_a", "stack_b"]:
            if stack_name in config.hardware:
                stack_config = config.hardware[stack_name]
                for model_role in ["primary", "secondary"]:
                    if model_role in stack_config.models:
                        model_cfg = stack_config.models[model_role]
                        expected_path = Path(model_cfg.get("path", ""))
                        if expected_path:
                            if expected_path.exists():
                                print(f"✓ {stack_name}.{model_role}: {expected_path.name} exists")
                            else:
                                print(f"⚠ {stack_name}.{model_role}: {expected_path.name} missing")
    except Exception as e:
        print(f"Note: Could not verify hardware configuration: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())