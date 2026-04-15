# CPU-Only Fallback (llama.cpp)

GlitchHunter v2.0 unterstützt vollständige CPU-only Inference via llama.cpp für Systeme ohne GPU.

## Übersicht

Das CPU-Fallback-System ermöglicht die Nutzung von GlitchHunter auf:
- Laptops ohne dedizierte GPU
- Servern ohne GPU
- VMs und Containern
- CI/CD-Pipelines

## Voraussetzungen

### Hardware

| Komponente | Minimum | Empfohlen |
|-----------|---------|-----------|
| CPU | 4 Kerne | 8+ Kerne |
| RAM | 8 GB | 16+ GB |
| Disk | 10 GB frei | SSD |

### Software

```bash
# llama.cpp bauen
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -DLLAMA_BLAS=ON  # Optional: BLAS für schnellere CPU
cmake --build build --config Release -j

# Binary verfügbar machen
export PATH=$PATH:/path/to/llama.cpp/build/bin
```

## Unterstützte Modelle

### Empfohlene GGUF-Modelle

| Modell | Größe | Quantisierung | RAM-Bedarf | Qualität |
|--------|-------|--------------|------------|----------|
| Qwen2.5-Coder-7B | 4.5 GB | Q4_K_M | ~6 GB | ⭐⭐⭐⭐ |
| DeepSeek-Coder-6.7B | 4.0 GB | Q4_K_M | ~5 GB | ⭐⭐⭐⭐ |
| Phi-4 | 2.8 GB | Q4_K_M | ~4 GB | ⭐⭐⭐ |
| CodeLlama-7B | 4.0 GB | Q4_K_M | ~5 GB | ⭐⭐⭐ |

### Download

```bash
# Automatischer Download
python -c "
from src.inference.llama_cpp_backend import LlamaCppBackend
backend = LlamaCppBackend()
backend.download_model('qwen2.5-coder-7b')
"

# Oder manuell mit huggingface-cli
huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF \
  qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  --local-dir ~/.glitchhunter/models
```

## Verwendung

### Automatische Erkennung

```bash
# Auto-Detection wählt CPU-Modus wenn keine GPU verfügbar
./scripts/run_auto.sh scan /path/to/repo
```

### Manuelle Aktivierung

```bash
# Force CPU-only
./scripts/run_auto.sh --cpu-only scan /path/to/repo

# Oder über Environment
export GLITCHHUNTER_CPU_ONLY=1
./scripts/run_auto.sh scan /path/to/repo
```

### Python API

```python
from src.inference.llama_cpp_backend import LlamaCppBackend, LlamaConfig

# Backend initialisieren
config = LlamaConfig(
    model_path="~/.glitchhunter/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
    context_size=4096,
    threads=-1,  # Alle Kerne nutzen
    temperature=0.2,
)

backend = LlamaCppBackend(config)
if backend.setup():
    # Generiere Fix
    response = backend.generate(
        prompt="Fix this SQL injection:\n\ndef query(user_input):\n    return f'SELECT * FROM users WHERE id = {user_input}'",
        max_tokens=512,
    )
    print(response)
```

## Hardware Auto-Detection

```python
from src.hardware.auto_detect import detect_hardware

# Erkennt beste verfügbare Hardware
rec = detect_hardware()

print(f"Backend: {rec.backend_name}")
print(f"Confidence: {rec.confidence}")
print(f"Reason: {rec.reason}")
print(f"Config: {rec.config}")

# Ausgabe ohne GPU:
# Backend: llama.cpp CPU
# Confidence: 0.95
# Reason: Keine GPU erkannt, CPU-Fallback aktiviert
# Config: {'threads': 8, 'context_size': 4096}
```

## Performance-Optimierung

### Threads konfigurieren

```python
# Auto (alle Kerne)
config = LlamaConfig(threads=-1)

# Manuelle Anzahl
config = LlamaConfig(threads=4)  # 4 Kerne
```

### BLAS-Acceleration

```bash
# Mit OpenBLAS (2-3x schneller)
cmake -B build -DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS

# Mit MKL (Intel CPUs)
cmake -B build -DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=Intel10_64lp
```

### Context-Größe

```python
# Kleinerer Context = schneller
config = LlamaConfig(
    context_size=2048,  # Für schnelle Scans
)
```

## Benchmarks

### Qwen2.5-Coder-7B (Q4_K_M)

| CPU | Threads | tok/sec | Latenz (256 tok) |
|-----|---------|---------|------------------|
| Ryzen 9 5900X | 12 | 15 | 17s |
| Intel i7-12700 | 12 | 12 | 21s |
| Ryzen 5 5600X | 6 | 8 | 32s |
| Intel i5-10400 | 6 | 6 | 43s |

### Vergleich: GPU vs CPU

| Task | RTX 3090 | Ryzen 9 5900X | Faktor |
|------|----------|---------------|--------|
| 10k LOC Scan | 2 min | 10 min | 5x |
| Einzel-Fix | 3s | 15s | 5x |
| Memory | 8 GB VRAM | 6 GB RAM | - |

## Ensemble mit CPU

```python
from src.ensemble.model_router import ModelRouter, ModelConfig
from src.hardware.auto_detect import BackendType

# CPU-Modell in Ensemble
models = [
    ModelConfig(
        model_id="local_cpu",
        model_name="Qwen2.5-Coder-7B-GGUF",
        backend_type=BackendType.CPU_LLAMA_CPP,
        weight=0.8,
    ),
    # API-Modelle als Backup
    ModelConfig(
        model_id="api_primary",
        model_name="Qwen2.5-Coder-32B",
        backend_type=BackendType.OPENAI_API,
        weight=1.2,
    ),
]

router = ModelRouter(models=models)
```

## Troubleshooting

### "llama-cli nicht gefunden"

```bash
# Finde Binary
which llama-cli

# Oder in gängigen Pfaden suchen
find /usr -name "llama-cli" 2>/dev/null

# PATH setzen
export PATH=$PATH:/path/to/llama.cpp/build/bin
```

### "Modell nicht gefunden"

```bash
# Download-Status prüfen
ls -la ~/.glitchhunter/models/

# Manuell herunterladen
wget https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  -O ~/.glitchhunter/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf
```

### Langsame Performance

1. BLAS aktivieren:
```bash
llama-cli --help | grep blas  # Prüfe BLAS-Support
```

2. Thread-Anzahl prüfen:
```python
import multiprocessing
print(multiprocessing.cpu_count())  # Sollte > 4 sein
```

3. Kleineres Modell verwenden:
```python
# Phi-4 ist schneller als Qwen 7B
config = LlamaConfig(model_path="phi-4-q4_k_m.gguf")
```

### OOM (Out of Memory)

1. Context-Größe reduzieren:
```python
config = LlamaConfig(context_size=2048)  # Statt 4096
```

2. Batch-Größe reduzieren:
```python
config = LlamaConfig(batch_size=256)  # Statt 512
```

3. Swap erhöhen:
```bash
sudo swapon /swapfile  # Falls vorhanden
```

## Konfiguration

### config.yaml

```yaml
hardware:
  auto_detect: true
  preferred_stack: "cpu"  # auto, a, b, cpu
  
  cpu_fallback:
    enabled: true
    threads: -1  # -1 = auto
    context_size: 4096
    batch_size: 512
    model: "qwen2.5-coder-7b-q4_k_m.gguf"
    
    # Performance
    use_blas: true
    blas_vendor: "OpenBLAS"  # OpenBLAS, Intel10_64lp
```

### Umgebungsvariablen

```bash
# llama.cpp Pfad
export LLAMA_CPP_PATH=/opt/llama.cpp/build/bin

# Modell-Verzeichnis
export GLITCHHUNTER_MODELS_DIR=/mnt/models

# Force CPU
export GLITCHHUNTER_CPU_ONLY=1

# Thread-Limit
export GLITCHHUNTER_CPU_THREADS=8
```

## Best Practices

1. **BLAS nutzen**: 2-3x Performance-Steigerung
2. **Passendes Modell**: 7B für Qualität, kleiner für Speed
3. **Context-Größe**: Nur so groß wie nötig
4. **Threads**: Alle physischen Kerne nutzen
5. **SSD**: Modelle auf SSD speichern
6. **Ensemble**: CPU + API für beste Balance