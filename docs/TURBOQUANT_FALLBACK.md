# TurboQuant Smart Fallback

GlitchHunter's TurboQuant-System nutzt jetzt intelligenten Fallback zwischen GPU und CPU - ohne Qualitätsverlust.

## Konzept

Statt separate CPU/GPU-Backends gibt es **ein einheitliches System**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TURBOQUANT SMART FALLBACK                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  EIN Backend (llama_cpp.py)                                        │
│         │                                                           │
│         ├─► GPU verfügbar + genug VRAM                             │
│         │   └── n_gpu_layers=-1  (Full TurboQuant)                 │
│         │                                                           │
│         ├─► GPU verfügbar, wenig VRAM                              │
│         │   └── n_gpu_layers=20  (Layer-Adaptive)                  │
│         │                                                           │
│         └─► Keine GPU oder --cpu-only                              │
│             └── n_gpu_layers=0   (CPU-Modus)                       │
│                                                                     │
│  Alle Optimierungen bleiben aktiv:                                 │
│  - KV-Cache Quantisierung                                          │
│  - Flash-Attention (wenn verfügbar)                                │
│  - Custom Kernels (CPU-taugliche)                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Modi

### 1. Full GPU Mode (n_gpu_layers=-1)

```python
# 8GB+ VRAM
config = get_inference_config()
# n_gpu_layers=-1  → Alle Layers auf GPU
# n_ctx=128000     → 128k Context
# flash_attn=True  → Flash-Attention aktiv
```

**Wann:** RTX 3060 12GB, RTX 3090/4090

### 2. Hybrid Mode (n_gpu_layers=10-30)

```python
# 4-8GB VRAM
config = get_inference_config()
# n_gpu_layers=20  → 20 Layers auf GPU, Rest CPU
# n_ctx=65536      → 64k Context
# Auto-Layer-Berechnung basierend auf VRAM
```

**Wann:** RTX 3060 8GB, GTX 1070/1080

### 3. CPU-Only Mode (n_gpu_layers=0)

```python
# Keine GPU oder --cpu-only
config = get_inference_config(cpu_only=True)
# n_gpu_layers=0   → Alles auf CPU
# n_threads=16     → Alle CPU-Kerne
# n_ctx=8192       → 8k Context (konservativ)
```

**Wann:** Laptops, Server, VMs, CI/CD

## Verwendung

### Automatisch (Empfohlen)

```python
from inference.engine import InferenceEngine

# Automatische Erkennung und Konfiguration
engine = InferenceEngine()
engine.load_model(
    model_path="/path/to/model.gguf",
    use_smart_fallback=True,  # Default: True
)
# Wählt automatisch Full GPU / Hybrid / CPU
```

### Manuelle Steuerung

```python
from hardware.smart_fallback import get_inference_config

# CPU erzwingen
config = get_inference_config(cpu_only=True)
print(f"Mode: {config.mode.value}")
print(f"GPU Layers: {config.n_gpu_layers}")
print(f"Threads: {config.n_threads}")

# Oder über Engine
engine.load_model(
    model_path="model.gguf",
    cpu_only=True,  # Erzwingt CPU-Modus
)
```

### Im ModelLoader

```python
from inference.model_loader import ModelLoader
from hardware.vram_manager import VRAMManager

vram_mgr = VRAMManager()
loader = ModelLoader(vram_mgr)

# Mit Smart Fallback
model = loader.load_model(
    model_config=config,
    use_smart_fallback=True,
)

# Ohne (Legacy-Verhalten)
model = loader.load_model(
    model_config=config,
    use_smart_fallback=False,
)
```

## Konfiguration

### config.yaml

```yaml
hardware:
  # Smart Fallback aktivieren
  smart_fallback: true
  
  # Thresholds für Modus-Selektion (GB)
  full_gpu_threshold: 8
  hybrid_threshold: 4
  
  # CPU-Only Override
  cpu_only: false  # Kann via --cpu-only gesetzt werden

inference:
  # Context-Größen by Mode
  context_full_gpu: 128000
  context_hybrid: 65536
  context_cpu: 8192
  
  # TurboQuant Optimierungen (immer aktiv)
  kv_cache_quantization: "q4_0"
  flash_attention: true
```

### CLI

```bash
# Automatisch
./scripts/run_auto.sh scan /path/to/repo

# CPU erzwingen
./scripts/run_auto.sh --cpu-only scan /path/to/repo

# Mit Environment-Variable
export GLITCHHUNTER_CPU_ONLY=1
./scripts/run_auto.sh scan /path/to/repo
```

## Performance-Vergleich

| Modus | GPU Layers | Context | Speed (7B Q4) | Anwendung |
|-------|------------|---------|---------------|-----------|
| Full GPU | -1 | 128k | ~25 tok/s | RTX 3090 |
| Hybrid | 20 | 64k | ~15 tok/s | RTX 3060 |
| CPU-Only | 0 | 8k | ~5 tok/s | Laptop |

## Migration von Alt-Code

### Vorher (Phase 1 Draft)

```python
# Alt: Separates CPU-Backend
from inference.llama_cpp_backend import LlamaCppBackend  # ENTFERNEN

backend = LlamaCppBackend()
backend.setup()
```

### Nachher (Smart Fallback)

```python
# Neu: Integriert in InferenceEngine
from inference.engine import InferenceEngine  # BEIBEHALTEN

engine = InferenceEngine()
engine.load_model(
    model_path="model.gguf",
    use_smart_fallback=True,  # NEU
)
```

## Troubleshooting

### "Insufficient VRAM" Warning

```
WARNING: Insufficient VRAM for model 'qwen' (6.00GB needed, 4.00GB available). 
         Attempting CPU fallback...
INFO: Falling back to CPU mode (threads=16)
```

**Lösung:** System funktioniert wie erwartet - automatischer Fallback.

### Flash-Attention nicht verfügbar

```
WARNING: Flash-Attention not available in CPU mode
```

**Normal:** Flash-Attention ist GPU-optimiert. Auf CPU wird standard Attention genutzt.

### Langsame Performance auf CPU

```python
# Threads erhöhen
config = get_inference_config(cpu_only=True)
config.n_threads = 32  # Falls mehr Kerne verfügbar
```

## Internals

### Ablauf

```python
1. User ruft engine.load_model() auf
         │
         ▼
2. SmartFallbackManager.detect_and_configure()
   ├── Prüft: cpu_only Flag?
   ├── Prüft: VRAM verfügbar?
   └── Wählt: FULL_GPU / HYBRID / CPU_ONLY
         │
         ▼
3. InferenceConfig.to_llama_kwargs()
   └── Baut kwargs für Llama()
         │
         ▼
4. Llama(**kwargs) geladen
   └── Alle TurboQuant-Opts aktiv
```

### Dateien

- `src/hardware/smart_fallback.py` - Fallback-Logik
- `src/inference/engine.py` - Integration
- `src/inference/model_loader.py` - Model Loading mit Fallback

## Vorteile

1. **Eine Codebase** - Keine Duplikation
2. **100% TurboQuant** - Alle Optimierungen erhalten
3. **Automatisch** - Keine manuelle Konfiguration nötig
4. **Graceful Degradation** - Läuft überall
5. **Zukunftssicher** - Neue Optimierungen profitieren alle Modi