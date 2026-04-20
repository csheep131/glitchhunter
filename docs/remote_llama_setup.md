# Remote Llama Server Setup

Dieses Dokument beschreibt, wie GlitchHunter mit einem remote im Netzwerk betriebenen Llama-Server konfiguriert wird.

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│  Lokales Netzwerk (192.168.x.x)                             │
│                                                             │
│  ┌─────────────────┐         ┌─────────────────────────┐   │
│  │ Llama-Server    │         │ GlitchHunter Instanzen  │   │
│  │ (Docker/Nativ)  │◄────────┤ - Stack A (GTX 3060)    │   │
│  │                 │ HTTP    │ - Stack B (RTX 3090)    │   │
│  │ - qwen3.5-9b    │ :8080   │ - TUI                   │   │
│  │ - phi-4-mini    │         │ - CLI                   │   │
│  │ - OpenAI-API    │         │ - API Server            │   │
│  └─────────────────┘         └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Voraussetzungen

- GPU-reicher Server im Netzwerk (mind. 8GB VRAM für 7B-Modelle, 16GB+ für größere)
- GlitchHunter-Clients im selben Netzwerk
- Offener Port 8080 (oder konfigurierter Port) auf dem Server

---

## Option A: llama.cpp Server (Docker)

### 1. Docker-Container starten

```bash
# Modell herunterladen (Beispiel: Qwen3.5-9B)
mkdir -p ~/llama-models
cd ~/llama-models
wget https://huggingface.co/Qwen/Qwen3.5-9B-Instruct-GGUF/resolve/main/qwen3.5-9b-instruct-q4_k_m.gguf

# Docker-Container mit GPU-Support starten
docker run -d \
  --name llama-server \
  --gpus all \
  -p 8080:8080 \
  -v ~/llama-models:/models:ro \
  --restart unless-stopped \
  ghcr.io/ggerganov/llama.cpp:server \
  --model /models/qwen3.5-9b-instruct-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 8192 \
  --n-gpu-layers 35 \
  --threads 8 \
  --batch-size 512 \
  --flash-attn
```

### 2. Server-URL ermitteln

```bash
# Server-IP herausfinden (auf dem Server)
hostname -I | awk '{print $1}'
# Ausgabe: 192.168.1.100
```

### 3. Health Check testen

```bash
curl http://localhost:8080/health
# Erwartete Antwort: {"status":"ok"}
```

---

## Option B: llama.cpp Server (Nativ)

### 1. llama.cpp bauen

```bash
# Repository klonen
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# Mit CUDA-Support bauen
make LLAMA_CUDA=1 -j$(nproc)

# Server binary kompilieren
make server -j$(nproc)
```

### 2. Server starten

```bash
./server \
  -m ~/models/qwen3.5-9b-instruct-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -c 8192 \
  -ngl 35 \
  -t 8 \
  --batch-size 512 \
  --flash-attn
```

### 3. Als Systemd-Service (optional)

```ini
# /etc/systemd/system/llama-server.service
[Unit]
Description=Llama.cpp Inference Server
After=network.target

[Service]
Type=simple
User=llama
WorkingDirectory=/home/llama/llama.cpp
ExecStart=/home/llama/llama.cpp/server \
  -m /home/llama/models/qwen3.5-9b-instruct-q4_k_m.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -c 8192 \
  -ngl 35 \
  -t 8
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Service aktivieren
sudo systemctl daemon-reload
sudo systemctl enable llama-server
sudo systemctl start llama-server
sudo systemctl status llama-server
```

---

## Option C: Ollama (Alternative)

### 1. Ollama installieren

```bash
# Installationsskript ausführen
curl -fsSL https://ollama.com/install.sh | sh

# Ollama als Service starten
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 2. Modell herunterladen

```bash
ollama pull qwen3.5:9b-instruct-q4_K_M
```

### 3. Konfiguration für OpenAI-kompatibles API

Ollama bietet unter `/v1/chat/completions` eine OpenAI-kompatible Schnittstelle.

```bash
# Testen
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5:9b-instruct-q4_K_M",
    "messages": [{"role": "user", "content": "Hallo!"}]
  }'
```

---

## Option D: vLLM (High-Performance Alternative)

### 1. vLLM installieren

```bash
pip install vllm
```

### 2. Server starten

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3.5-9B-Instruct \
  --host 0.0.0.0 \
  --port 8080 \
  --tensor-parallel-size 1 \
  --max-model-len 8192
```

---

## GlitchHunter Konfiguration

### Methode 1: Environment Variable (Empfohlen)

```bash
# Auf jedem GlitchHunter-Client
export LLAMA_NETWORK_URL="http://192.168.1.100:8080"

# GlitchHunter starten
python -m src.main
```

### Methode 2: config.yaml

```yaml
# config.yaml
inference:
  mode: "remote"  # oder "local"
  remote_base_url: "http://192.168.1.100:8080"
  remote_fallback_to_local: true  # Bei Server-Ausfall lokal laden
  remote_timeout: 120  # Request-Timeout in Sekunden
```

### Methode 3: Programmatisch

```python
from inference.engine import InferenceEngine

engine = InferenceEngine(
    model_name="qwen3.5-9b",
    api_url="http://192.168.1.100:8080"
)
engine.load_model()  # Verbindet remote
```

---

## Netzwerk-Konfiguration

### Firewall-Regeln

```bash
# Auf dem Llama-Server (UFW)
sudo ufw allow 8080/tcp comment "Llama Server"
sudo ufw reload

# Oder mit iptables
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
```

### mDNS / Avahi (Optional für automatische Discovery)

```bash
# Avahi installieren
sudo apt install avahi-daemon

# Service registrieren
cat > /etc/avahi/services/llama-server.service <<EOF
<?xml version="1.0" standalone='no'?>
<service-group>
  <name replace-wildcards="yes">GlitchHunter Llama Server</name>
  <service>
    <type>_http._tcp</type>
    <port>8080</port>
  </service>
</service-group>
EOF

sudo systemctl restart avahi-daemon
```

Danach erreichbar via: `http://llama-server.local:8080`

---

## Security

### API-Key Authentifizierung (Empfohlen für Produktion)

```bash
# llama.cpp Server mit Auth starten
./server \
  -m model.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --api-key "dein-geheimer-api-key"
```

```yaml
# config.yaml
inference:
  remote_base_url: "http://192.168.1.100:8080"
  remote_api_key: "dein-geheimer-api-key"
```

### VPN für Remote-Zugriff

Für Zugriff außerhalb des lokalen Netzwerks:
- WireGuard VPN einrichten
- Tailscale verwenden (einfachste Option)

```bash
# Tailscale auf Server und Clients
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Server erreichbar via Tailscale-IP: 100.x.y.z
```

---

## Load Balancing (Multi-Server)

Für mehrere Llama-Server im Netzwerk:

```yaml
# config.yaml
inference:
  remote_servers:
    - url: "http://192.168.1.100:8080"
      models: ["qwen3.5-9b", "phi-4-mini"]
      weight: 1.0
    - url: "http://192.168.1.101:8080"
      models: ["deepseek-v3.2-small"]
      weight: 0.5
  load_balancing_strategy: "round_robin"  # oder "least_loaded"
```

---

## Troubleshooting

### Server nicht erreichbar

```bash
# Connectivity testen
curl http://192.168.1.100:8080/health

# Port prüfen
nc -zv 192.168.1.100 8080

# Firewall prüfen
sudo ufw status
```

### Langsame Inferenz

- GPU-Auslastung prüfen: `nvidia-smi`
- VRAM-Nutzung optimieren: `--n-gpu-layers` anpassen
- Context-Size reduzieren: `--ctx-size 4096`
- Batch-Size optimieren: `--batch-size 256`

### Model lädt nicht

- Pfad prüfen: `ls -la /models/`
- Berechtigungen: `chmod 644 model.gguf`
- Modell-Kompatibilität: GGUF Format required

---

## Monitoring

### Prometheus Metrics (llama.cpp)

```bash
# Server mit Metrics starten
./server \
  -m model.gguf \
  --port 8080 \
  --metrics-port 9090
```

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'llama-server'
    static_configs:
      - targets: ['192.168.1.100:9090']
```

### Grafana Dashboard

Importiere Dashboard ID `19005` (vLLM) oder erstelle custom Dashboard für:
- Requests pro Sekunde
- Durchschnittliche Latenz
- GPU-Auslastung
- VRAM-Nutzung

---

## Performance-Tuning

### Optimale Einstellungen für verschiedene GPUs

| GPU | VRAM | Model | n_gpu_layers | ctx_size |
|-----|------|-------|--------------|----------|
| GTX 3060 | 12GB | qwen3.5-9b | 35 | 8192 |
| RTX 3080 | 10GB | qwen3.5-9b | 30 | 8192 |
| RTX 3090 | 24GB | qwen3.5-27b | 50 | 16384 |
| RTX 4090 | 24GB | qwen3.5-35b | 55 | 16384 |
| A100 | 40GB | qwen3.5-72b | 80 | 32768 |

### Flash Attention

Für Ampere (RTX 30xx/40xx) und neuer:
```bash
--flash-attn
```

### Quantisierung

- Q4_K_M: Bester Kompromiss (empfohlen)
- Q5_K_M: Höhere Qualität, mehr VRAM
- Q3_K_S: Minimale VRAM, Qualitätseinbußen

---

## Kosten-Nutzen-Analyse

| Szenario | Lokale GPUs | Remote Server | Einsparung |
|----------|-------------|---------------|------------|
| 5 Entwickler | 5x 8GB VRAM | 1x 24GB VRAM | ~4 GPUs |
| Wartung | 5x Updates | 1x Update | 80% weniger |
| Stromverbrauch | ~1500W | ~450W | ~70% |

---

## Next Steps

1. **Proof of Concept**: Manuelles Testen mit `curl`
2. **Docker-Setup**: Container aufsetzen
3. **GlitchHunter Integration**: Config anpassen
4. **Produktion**: Security & Monitoring aktivieren
