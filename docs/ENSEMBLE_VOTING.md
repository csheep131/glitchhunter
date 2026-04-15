# Ensemble Voting System

GlitchHunter v2.0 nutzt ein Multi-Model Ensemble Voting System für höchste Fix-Qualität.

## Übersicht

Das Ensemble-System koordiniert mehrere LLMs (z.B. Qwen2.5-Coder, DeepSeek-Coder, Phi-4) die parallel Fixes generieren und über den besten abstimmen.

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                     ENSEMBLE PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: Bug Report + Code Context                          │
│                    ↓                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Qwen      │  │  DeepSeek   │  │    Phi-4    │         │
│  │  32B Param  │  │  6.7B Param │  │  2.7B Param │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         ↓                ↓                ↓                 │
│    Fix Proposal    Fix Proposal    Fix Proposal             │
│    Confidence: 88  Confidence: 92  Confidence: 75          │
│         ↓                ↓                ↓                 │
│         └────────────────┼────────────────┘                 │
│                          ↓                                  │
│              ┌───────────────────────┐                      │
│              │    VotingEngine       │                      │
│              │  (Strategy: weighted) │                      │
│              └───────────┬───────────┘                      │
│                          ↓                                  │
│              Winning Fix: DeepSeek's Proposal               │
│              Agreement: 2/3 models (67%)                    │
│              Final Confidence: 91.2                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Voting-Strategien

### 1. Majority Voting
Einfache Mehrheitsentscheidung. Der Fix mit den meisten identischen Vorschlägen gewinnt.

```python
from src.ensemble import VotingEngine, VoteStrategy

engine = VotingEngine(strategy=VoteStrategy.MAJORITY)
```

### 2. Weighted Voting (Default)
Berücksichtigt Modell-Performance und konfigurierte Gewichtungen.

```python
engine = VotingEngine(strategy=VoteStrategy.WEIGHTED)
engine.register_model("qwen", weight=1.2)
engine.register_model("deepseek", weight=1.0)
engine.register_model("local", weight=0.8)
```

### 3. Confidence Voting
Wählt den Fix mit der höchsten Konfidenz.

```python
engine = VotingEngine(strategy=VoteStrategy.CONFIDENCE)
```

### 4. Consensus Voting
Erfordert 75% Übereinstimmung. Falls nicht erreicht, Fallback zu Weighted.

```python
engine = VotingEngine(strategy=VoteStrategy.CONSENSUS)
```

## Verwendung

### Basis-Verwendung

```python
import asyncio
from src.ensemble import VotingEngine, VoteStrategy, ModelVote
from src.ensemble.model_router import ModelRouter

async def main():
    # Initialisiere Router mit mehreren Modellen
    router = ModelRouter()
    await router.initialize()
    
    # Erstelle Voting Engine
    engine = VotingEngine(
        strategy=VoteStrategy.WEIGHTED,
        min_confidence=0.7,
        timeout_seconds=60,
    )
    
    # Generiere parallele Model-Calls
    prompt = "Fix this SQL injection vulnerability..."
    model_calls = [
        lambda: router.generate_single("qwen", prompt),
        lambda: router.generate_single("deepseek", prompt),
        lambda: router.generate_single("local", prompt),
    ]
    
    # Führe Voting durch
    result = await engine.vote(model_calls)
    
    print(f"Winning model: {result.winning_model}")
    print(f"Confidence: {result.confidence_score:.2f}")
    print(f"Agreement: {result.agreement_ratio:.0%}")
    print(f"Fix:\n{result.winning_fix}")

asyncio.run(main())
```

### Mit Caching

```python
# Context-Hash für Caching
import hashlib
context_hash = hashlib.sha256((code + bug_description).encode()).hexdigest()

result = await engine.vote(model_calls, context_hash=context_hash)
# Bei Cache-Hit: Sofortige Rückgabe ohne LLM-Calls
```

## VoteResult Struktur

```python
@dataclass
class VoteResult:
    winning_fix: str           # Der ausgewählte Fix
    winning_model: str         # Gewinner-Modell
    confidence_score: float    # 0.0 - 1.0
    strategy_used: VoteStrategy
    total_votes: int
    agreement_ratio: float     # Übereinstimmungsquote
    all_votes: List[ModelVote] # Alle Stimmen
    consensus_reached: bool
    explanation: str           # Natürlichsprachliche Erklärung
```

## Performance-Tracking

```python
# Zeige Modell-Performance
stats = engine.get_model_stats()
for model_id, perf in stats.items():
    print(f"{model_id}:")
    print(f"  Calls: {perf['total_calls']}")
    print(f"  Avg Confidence: {perf['avg_confidence']:.2f}")
    print(f"  Avg Response Time: {perf['avg_response_time']:.0f}ms")
```

## Konfiguration

In `config.yaml`:

```yaml
ensemble:
  enabled: true
  strategy: "weighted"
  min_confidence: 0.7
  timeout_seconds: 60
  models:
    - id: "qwen"
      name: "Qwen2.5-Coder-32B"
      backend: "openai_api"
      weight: 1.2
    - id: "deepseek"
      name: "DeepSeek-Coder-V2"
      backend: "openai_api"
      weight: 1.0
    - id: "local"
      name: "Qwen2.5-Coder-7B-GGUF"
      backend: "llama_cpp"
      weight: 0.8
```

## API-Endpunkte

### POST /api/v2/analyze

```bash
curl -X POST http://localhost:8000/api/v2/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "...",
    "use_ensemble": true,
    "strategy": "weighted",
    "models": ["qwen", "deepseek", "local"]
  }'
```

Response:
```json
{
  "fix": "...",
  "confidence": 0.92,
  "ensemble_result": {
    "winning_model": "deepseek",
    "agreement_ratio": 0.67,
    "consensus_reached": false,
    "total_votes": 3,
    "all_votes": [...]
  }
}
```

## Troubleshooting

### Timeout bei Ensemble
Erhöhe `timeout_seconds` oder reduziere Anzahl der Modelle:
```python
engine = VotingEngine(timeout_seconds=120)
```

### Niedrige Agreement Ratio
Wechsle zu `CONSENSUS` Strategie für höhere Qualität:
```python
engine = VotingEngine(strategy=VoteStrategy.CONSENSUS)
```

### Cache invalidieren
```python
engine._fix_cache.clear()
```