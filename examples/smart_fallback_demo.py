#!/usr/bin/env python3
"""
Smart Fallback Demo - Zeigt TurboQuant GPU/CPU Fallback

Dieses Beispiel zeigt wie GlitchHunter automatisch zwischen
GPU- und CPU-Modus wechselt - ohne Code-Änderungen.
"""

import sys
sys.path.insert(0, '/home/schaf/projects/glitchhunter/src')

from hardware.smart_fallback import (
    get_inference_config,
    InferenceMode,
    SmartFallbackManager,
)


def show_detected_config():
    """Zeigt die automatisch erkannte Konfiguration."""
    print("=" * 60)
    print("GlitchHunter TurboQuant Smart Fallback")
    print("=" * 60)
    print()
    
    # Detect hardware
    manager = SmartFallbackManager()
    config = manager.detect_and_configure()
    
    print(f"Erkannter Modus: {config.mode.value.upper()}")
    print(f"Beschreibung: {manager.get_mode_description(config)}")
    print()
    print("Konfiguration:")
    print(f"  n_gpu_layers: {config.n_gpu_layers} ({_explain_gpu_layers(config.n_gpu_layers)})")
    print(f"  n_threads: {config.n_threads}")
    print(f"  n_ctx: {config.n_ctx:,} tokens")
    print(f"  batch_size: {config.batch_size}")
    print()
    print("TurboQuant Optimierungen:")
    print(f"  use_turboquant: {config.use_turboquant}")
    print(f"  flash_attention: {config.flash_attention}")
    print(f"  kv_cache_quant: {config.kv_cache_quantization}")
    print()
    
    return config


def _explain_gpu_layers(n: int) -> str:
    """Erklärt die Bedeutung von n_gpu_layers."""
    if n == -1:
        return "Alle Layers auf GPU (Full GPU)"
    elif n == 0:
        return "CPU-Only"
    else:
        return f"{n} Layers auf GPU, Rest CPU (Hybrid)"


def demo_all_modes():
    """Zeigt alle drei Modi (für Debugging/Tests)."""
    print()
    print("=" * 60)
    print("Alle Modi (Simulation)")
    print("=" * 60)
    print()
    
    modes = [
        (InferenceMode.FULL_GPU, "RTX 3090/4090 (24GB)"),
        (InferenceMode.HYBRID, "RTX 3060 (8GB)"),
        (InferenceMode.CPU_ONLY, "Laptop/Server (Keine GPU)"),
    ]
    
    for mode, description in modes:
        print(f"{description}:")
        
        # Force specific mode
        config = get_inference_config(force_mode=mode)
        
        print(f"  Mode: {config.mode.value}")
        print(f"  GPU Layers: {config.n_gpu_layers}")
        print(f"  Context: {config.n_ctx:,}")
        print(f"  Threads: {config.n_threads}")
        print()


def demo_cpu_only():
    """Demo: CPU-Only Modus erzwingen."""
    print()
    print("=" * 60)
    print("CPU-Only Modus (erzwungen)")
    print("=" * 60)
    print()
    
    config = get_inference_config(cpu_only=True)
    
    print(f"Mode: {config.mode.value}")
    print(f"GPU Layers: {config.n_gpu_layers}")
    print(f"Threads: {config.n_threads} (nutzt alle CPU-Kerne)")
    print()
    print("Verwendung:")
    print("  from inference.engine import InferenceEngine")
    print("  engine = InferenceEngine()")
    print("  engine.load_model('model.gguf', cpu_only=True)")
    print()


def demo_llama_kwargs():
    """Zeigt die generierten llama.cpp Parameter."""
    print()
    print("=" * 60)
    print("Llama.cpp Parameter")
    print("=" * 60)
    print()
    
    config = get_inference_config()
    kwargs = config.to_llama_kwargs()
    
    print("kwargs für Llama(**kwargs):")
    for key, value in kwargs.items():
        print(f"  {key}: {value}")
    print()


def main():
    """Hauptfunktion."""
    # 1. Zeige automatisch erkannte Konfiguration
    config = show_detected_config()
    
    # 2. Zeige alle Modi
    demo_all_modes()
    
    # 3. CPU-Only Demo
    demo_cpu_only()
    
    # 4. Llama.cpp Parameter
    demo_llama_kwargs()
    
    print()
    print("=" * 60)
    print("Fazit")
    print("=" * 60)
    print()
    print("Ein Backend, drei Modi:")
    print("  - Full GPU: Alle Layers auf GPU (schnellster)")
    print("  - Hybrid: Teilweise GPU-Offload (ausgewogen)")
    print("  - CPU: Keine GPU nötig (kompatibel)")
    print()
    print("Alle TurboQuant-Optimierungen aktiv in allen Modi!")
    print()


if __name__ == "__main__":
    main()