# GlitchHunter

🔍 **AI-powered code analysis with adaptive hardware support**

GlitchHunter is an intelligent code analysis tool that automatically adapts to available hardware and uses different analysis stacks depending on GPU resources.

## Features

- **Adaptive hardware detection**: Automatic selection between Stack A (8GB VRAM) and Stack B (24GB VRAM)
- **Two-stage analysis**: Pre-filter with AST + security scan, followed by AI-powered deep analysis
- **Multi-model inference**: Support for Qwen3.5, Phi-4-mini, DeepSeek-V3.2
- **OWASP Top 10 2025**: Complete security coverage including API Security
- **LangGraph state machine**: 5-state agent for iterative code verification
- **OpenAI-compatible API**: Easy integration into existing workflows

## Hardware Stacks

| Feature | Stack A (GTX 3060) | Stack B (RTX 3090) |
|---------|-------------------|-------------------|
| VRAM | 8GB | 24GB |
| Models | Qwen3.5-9B + Phi-4-mini | Qwen3.5-27B/35B + DeepSeek-V3.2-Small |
| Mode | Sequential | Parallel |
| Security | Security-Lite | Full Security Shield |
| Throughput | ~50 LOC/min | ~200 LOC/min |

## Quickstart

### Prerequisites

- Python 3.10+
- NVIDIA GPU with CUDA 12.x
- Docker (for sandbox execution)
- cmake, build-essential

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/glitchhunter.git
cd glitchunter

# Install dependencies
pip install -r requirements.txt

# Build llama-cpp-python for GPU
./scripts/build_llama_cpp.sh

# Download models
python scripts/download_models.py
```

### Start Stack A (GTX 3060)

```bash
./scripts/run_stack_a.sh
```

### Start Stack B (RTX 3090)

```bash
./scripts/run_stack_b.sh
```

### Using the API

```bash
# Start server
python -m src.api.server --host 0.0.0.0 --port 8000

# Request analysis
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"code": "def vulnerable(): eval(user_input)", "language": "python"}'
```

## Project Structure

```
glitchunter/
├── src/
│   ├── hardware/      # Hardware detection and VRAM management
│   ├── inference/     # Model inference with llama-cpp
│   ├── prefilter/     # AST analysis and complexity checks
│   ├── security/      # OWASP scanner and security shield
│   ├── agent/         # LangGraph state machine
│   ├── mapper/        # Repository mapping and symbol graph
│   ├── api/           # FastAPI server and routes
│   └── core/          # Config, logging, exceptions
├── scripts/           # Build and run scripts
├── tests/             # Unit tests
└── docs/              # Documentation
```

## Configuration

The `config.yaml` controls all hardware profiles and feature toggles:

```yaml
hardware:
  stack_a:
    vram_limit: 8GB
    models: [qwen3.5-9b, phi-4-mini]
    mode: sequential
    security: lite
  
  stack_b:
    vram_limit: 24GB
    models: [qwen3.5-27b, deepseek-v3.2-small]
    mode: parallel
    security: full
```

## Tests

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request