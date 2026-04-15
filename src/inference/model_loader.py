"""
Model loader for GlitchHunter.

Manages model loading, unloading, and VRAM allocation with support for
multiple model types (Qwen, Phi, DeepSeek).
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.exceptions import ModelLoadError
from hardware.profiles import ModelConfig
from hardware.vram_manager import VRAMManager

logger = logging.getLogger(__name__)

# Model type detection based on name patterns
MODEL_TYPE_PATTERNS = {
    "qwen": ["qwen", "Qwen"],
    "phi": ["phi", "Phi"],
    "deepseek": ["deepseek", "DeepSeek"],
    "llama": ["llama", "Llama"],
}


class ModelLoader:
    """
    Manages model loading and lifecycle.

    Handles VRAM allocation, model loading from GGUF files, and provides
    status tracking for loaded models.

    Attributes:
        vram_manager: VRAM manager for allocation tracking
        loaded_models: Dictionary of currently loaded models
    """

    def __init__(self, vram_manager: VRAMManager) -> None:
        """
        Initialize model loader.

        Args:
            vram_manager: VRAM manager for allocation tracking
        """
        self._vram_manager = vram_manager
        self._loaded_models: Dict[str, Dict[str, Any]] = {}

        logger.debug("ModelLoader initialized")

    def load_model(
        self,
        model_config: ModelConfig,
        model_alias: Optional[str] = None,
        use_smart_fallback: bool = True,
    ) -> Any:
        """
        Load a model from file with smart GPU/CPU fallback.

        Args:
            model_config: Model configuration with path and parameters
            model_alias: Optional alias for the loaded model
            use_smart_fallback: Enable intelligent fallback based on VRAM

        Returns:
            Loaded model instance (llama-cpp-python Llama object)

        Raises:
            ModelLoadError: If model loading fails
        """
        alias = model_alias or model_config.name

        # Check if already loaded
        if alias in self._loaded_models:
            logger.info(f"Model '{alias}' already loaded, returning existing instance")
            return self._loaded_models[alias]["model"]

        # Validate model file exists
        model_path = Path(model_config.path)
        if not model_path.exists():
            raise ModelLoadError(
                f"Model file not found: {model_path}",
                details={
                    "model_name": model_config.name,
                    "expected_path": str(model_path),
                },
            )

        # Use smart fallback to determine optimal settings
        if use_smart_fallback:
            from hardware.smart_fallback import get_inference_config
            
            # Detect if CPU-only is needed
            cpu_only = model_config.n_gpu_layers == 0
            inference_config = get_inference_config(cpu_only=cpu_only)
            
            # Update model config with smart settings
            effective_config = ModelConfig(
                name=model_config.name,
                path=model_config.path,
                context_length=min(model_config.context_length, inference_config.n_ctx),
                n_gpu_layers=inference_config.n_gpu_layers,
                n_threads=inference_config.n_threads,
            )
            
            logger.info(f"Smart fallback: {inference_config.mode.value}, "
                       f"n_gpu_layers={inference_config.n_gpu_layers}")
        else:
            effective_config = model_config

        # Estimate VRAM requirement
        estimated_vram = self._estimate_vram_requirement(effective_config)

        # Allocate VRAM
        allocated = self._vram_manager.allocate_for_model(
            model_name=alias,
            required_vram_gb=estimated_vram,
            context_length=effective_config.context_length,
            batch_size=1,
        )

        if not allocated:
            available = self._vram_manager.available_vram_gb
            logger.warning(
                f"Insufficient VRAM for model '{alias}' ({estimated_vram:.2f}GB needed, "
                f"{available:.2f}GB available). Attempting CPU fallback..."
            )
            
            # Force CPU mode and retry
            effective_config.n_gpu_layers = 0
            effective_config.n_threads = multiprocessing.cpu_count()
            logger.info(f"Falling back to CPU mode (threads={effective_config.n_threads})")

        # Load model
        try:
            logger.info(f"Loading model '{alias}' from {model_path}")

            from llama_cpp import Llama
            from hardware.smart_fallback import InferenceMode

            # Build kwargs with TurboQuant optimizations
            load_kwargs = {
                "model_path": str(model_path),
                "n_ctx": effective_config.context_length,
                "n_gpu_layers": effective_config.n_gpu_layers,
                "n_threads": effective_config.n_threads,
                "verbose": False,
            }
            
            # Add TurboQuant optimizations if available
            if use_smart_fallback:
                inference_config = get_inference_config(
                    cpu_only=(effective_config.n_gpu_layers == 0)
                )
                turbo_kwargs = inference_config.to_llama_kwargs()
                load_kwargs.update(turbo_kwargs)

            model = Llama(**load_kwargs)

            # Track loaded model
            self._loaded_models[alias] = {
                "model": model,
                "config": effective_config,
                "vram_allocated": estimated_vram if effective_config.n_gpu_layers > 0 else 0,
            }

            mode_str = "GPU" if effective_config.n_gpu_layers != 0 else "CPU"
            logger.info(
                f"Model '{alias}' loaded successfully ({mode_str} mode, "
                f"layers={effective_config.n_gpu_layers}, ctx={effective_config.context_length})"
            )

            return model

        except ImportError as e:
            # Release VRAM allocation on failure
            self._vram_manager.release_for_model(alias)
            raise ModelLoadError(
                "llama-cpp-python not installed",
                details={"error": str(e)},
            )

        except Exception as e:
            # Release VRAM allocation on failure
            self._vram_manager.release_for_model(alias)
            raise ModelLoadError(
                f"Failed to load model: {e}",
                details={
                    "model_name": alias,
                    "model_path": str(model_path),
                    "error": str(e),
                },
            )

    def unload_model(self, model_alias: str) -> bool:
        """
        Unload a model and release VRAM.

        Args:
            model_alias: Alias of the model to unload

        Returns:
            True if unloaded successfully, False if not found
        """
        if model_alias not in self._loaded_models:
            logger.warning(f"Model '{model_alias}' not found for unload")
            return False

        logger.info(f"Unloading model '{model_alias}'")

        # Delete model reference
        del self._loaded_models[model_alias]["model"]

        # Release VRAM
        self._vram_manager.release_for_model(model_alias)

        # Remove from tracking
        del self._loaded_models[model_alias]

        logger.info(f"Model '{model_alias}' unloaded successfully")
        return True

    def unload_all_models(self) -> None:
        """Unload all loaded models and release all VRAM."""
        aliases = list(self._loaded_models.keys())
        for alias in aliases:
            self.unload_model(alias)
        logger.info("All models unloaded")

    def is_loaded(self, model_alias: str) -> bool:
        """
        Check if a model is loaded.

        Args:
            model_alias: Alias of the model

        Returns:
            True if model is loaded
        """
        return model_alias in self._loaded_models

    def get_model(self, model_alias: str) -> Optional[Any]:
        """
        Get a loaded model instance.

        Args:
            model_alias: Alias of the model

        Returns:
            Model instance or None if not loaded
        """
        if model_alias in self._loaded_models:
            return self._loaded_models[model_alias]["model"]
        return None

    def get_model_info(self, model_alias: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a loaded model.

        Args:
            model_alias: Alias of the model

        Returns:
            Dictionary with model information or None
        """
        if model_alias not in self._loaded_models:
            return None

        model_data = self._loaded_models[model_alias]
        return {
            "alias": model_alias,
            "name": model_data["config"].name,
            "path": model_data["config"].path,
            "context_length": model_data["config"].context_length,
            "vram_allocated_gb": model_data["vram_allocated"],
        }

    def list_loaded_models(self) -> Dict[str, Dict[str, Any]]:
        """
        List all currently loaded models.

        Returns:
            Dictionary of loaded models with their information
        """
        return {
            alias: {
                "name": data["config"].name,
                "path": data["config"].path,
                "context_length": data["config"].context_length,
                "vram_allocated_gb": data["vram_allocated"],
            }
            for alias, data in self._loaded_models.items()
        }

    def _estimate_vram_requirement(self, model_config: ModelConfig) -> float:
        """
        Estimate VRAM requirement for a model.

        Args:
            model_config: Model configuration

        Returns:
            Estimated VRAM in GB
        """
        # Base VRAM for model weights (varies by model size and quantization)
        # Q4_K_M quantization: ~4-5 bits per parameter
        model_name_lower = model_config.name.lower()

        if "35b" in model_name_lower or "34b" in model_name_lower:
            base_vram = 20.0  # ~35B parameters Q4
        elif "27b" in model_name_lower:
            base_vram = 16.0  # ~27B parameters Q4
        elif "13b" in model_name_lower:
            base_vram = 8.0  # ~13B parameters Q4
        elif "9b" in model_name_lower or "8b" in model_name_lower:
            base_vram = 6.0  # ~9B parameters Q4
        elif "7b" in model_name_lower:
            base_vram = 5.0  # ~7B parameters Q4
        elif "mini" in model_name_lower or "small" in model_name_lower:
            base_vram = 3.0  # Small models
        else:
            base_vram = 5.0  # Default estimate

        # Add VRAM for context (KV cache)
        # Approximate: 1GB per 8K context for large models
        context_vram = (model_config.context_length / 8192) * 2.0

        # Total estimate with safety margin
        total_vram = base_vram + context_vram

        logger.debug(
            f"Estimated VRAM for {model_config.name}: "
            f"{total_vram:.2f}GB (base={base_vram:.1f}, context={context_vram:.1f})"
        )

        return total_vram

    def get_vram_status(self) -> Dict[str, Any]:
        """
        Get VRAM usage status.

        Returns:
            Dictionary with VRAM information
        """
        return self._vram_manager.get_status()

    def __len__(self) -> int:
        """Return number of loaded models."""
        return len(self._loaded_models)

    def __contains__(self, model_alias: str) -> bool:
        """Check if model is loaded."""
        return model_alias in self._loaded_models
