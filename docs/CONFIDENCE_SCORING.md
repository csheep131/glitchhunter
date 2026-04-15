# Fix Confidence Scoring

GlitchHunter v2.0 bewertet jeden Fix mit einem detaillierten Confidence Score (0-100) und einer natürlichsprachlichen Erklärung.

## Faktoren

Der Confidence Score setzt sich aus 5 Faktoren zusammen:

| Faktor | Gewicht | Beschreibung |
|--------|---------|--------------|
| Syntax Validity | 20% | Code ist syntaktisch korrekt |
| Test Preservation | 25% | Bestehende Tests laufen weiter |
| No New Dependencies | 15% | Keine neuen Imports/Libraries |
| API Compatibility | 20% | API-Änderungen sind kompatibel |
| Semantic Correctness | 20% | Logik ist semantisch korrekt |

## Berechnung

```
Overall Score = Σ(Faktor_Score × Gewicht)

Beispiel:
  Syntax:          100 × 0.20 = 20.0
  Tests:            95 × 0.25 = 23.75
  Dependencies:    100 × 0.15 = 15.0
  API:              85 × 0.20 = 17.0
  Semantics:        90 × 0.20 = 18.0
  ──────────────────────────────────
  Overall:                         93.75
```

## Confidence Level

| Score | Level | Bedeutung |
|-------|-------|-----------|
| 90-100 | High | Fix kann automatisch angewendet werden |
| 70-89 | Medium | Fix empfohlen, aber Review empfohlen |
| 0-69 | Low | Manuelle Review erforderlich |

## Verwendung

### Basis-Verwendung

```python
from src.ensemble import ConfidenceCalculator

calculator = ConfidenceCalculator()

score = calculator.calculate(
    original_code=original,
    fixed_code=fixed,
    file_path="src/vulnerable.py",
    test_results={"total": 20, "passed": 19},
)

print(f"Score: {score.overall_score}/100 ({score.confidence_level})")
print(f"Explanation: {score.explanation}")

for factor, value in score.factors.items():
    print(f"  {factor.value}: {value}/100")
```

### Ausgabe-Format

```
Fix Confidence: 92/100 (high)

Stärken: Syntax Validity, No New Dependencies
Achtung bei: API Compatibility

Fix Confidence: 92% – Hervorragende Qualität. 
Keine neuen Abhängigkeiten, API-Änderung dokumentieren.

Warnings:
  ⚠ API-Inkompatibilität erkannt

Recommendations:
  - API-Änderungen dokumentieren
  - Integrationstests erweitern
```

## Faktor-Details

### Syntax Validity

Prüft ob der generierte Code syntaktisch korrekt ist.

```python
def _check_syntax_validity(self, code: str, file_path: str) -> float:
    if file_path.endswith('.py'):
        try:
            ast.parse(code)
            return 100.0
        except SyntaxError:
            return 0.0
    # ... andere Sprachen
```

**Scoring:**
- 100: Keine Syntaxfehler
- 0: Syntaxfehler gefunden

### Test Preservation

Prüft ob bestehende Tests weiterhin bestehen.

```python
score = calculator.calculate(
    original_code=original,
    fixed_code=fixed,
    test_results={"total": 20, "passed": 19, "failed": 1},
)
# Score: 19/20 = 95%
```

**Scoring:**
- 100: Alle Tests bestehen
- 0-99: Proportional zu bestandenen Tests
- 75: Keine Test-Ergebnisse verfügbar (neutral)

### No New Dependencies

Erkennt neue Imports und externe Abhängigkeiten.

```python
# Original
import json

# Fixed
import json
import requests  # ← Neue externe Dependency
import hashlib   # ← OK (Standard-Library)
```

**Scoring:**
- 100: Keine neuen Dependencies
- -20 pro neuer externer Dependency
- Standard-Library Imports: Kein Abzug

### API Compatibility

Prüft auf Breaking Changes in öffentlichen APIs.

```python
# Original
def process(data): ...

# Fixed (Inkompatibel)
def process(data, new_param): ...  # ← Breaking Change
```

**Scoring:**
- 100: Keine API-Änderungen
- -25 pro geänderter Funktionssignatur
- -30 pro entfernter öffentlicher Funktion

### Semantic Correctness

Bewertet die semantische Korrektheit durch Heuristiken.

**Checks:**
- Code-Größe (zu viele Änderungen = verdächtig)
- Verdächtige Patterns (`eval`, `exec`, `__import__`)
- Komplexitäts-Änderungen

**Scoring:**
- 100: Keine Probleme
- -10 bei signifikanter Größenänderung
- -30 bei verdächtigen Patterns

## Anpassung

### Gewichtung ändern

```python
calculator = ConfidenceCalculator()
calculator.factor_weights = {
    ConfidenceFactor.SYNTAX_VALIDITY: 0.15,
    ConfidenceFactor.TEST_PRESERVATION: 0.30,  # Mehr Gewicht auf Tests
    ConfidenceFactor.NO_NEW_DEPS: 0.15,
    ConfidenceFactor.API_COMPATIBILITY: 0.20,
    ConfidenceFactor.SEMANTIC_CORRECTNESS: 0.20,
}
```

### Mindest-Score konfigurieren

In `config.yaml`:

```yaml
confidence:
  min_overall_score: 80  # Default: 70
  auto_apply_threshold: 90  # Ab dieser Punktzahl automatisch anwenden
```

## Integration

### Im Patch Loop

```python
from src.agent.patch_loop import PatchLoop
from src.ensemble import ConfidenceCalculator

class PatchLoop:
    async def apply_fix(self, fix):
        # Generiere Fix
        fixed_code = await self.generate_fix(fix)
        
        # Berechne Confidence
        calculator = ConfidenceCalculator()
        score = calculator.calculate(
            original_code=original,
            fixed_code=fixed_code,
            file_path=fix.file_path,
            test_results=await self.run_tests(),
        )
        
        # Nur anwenden wenn Confidence hoch genug
        if score.confidence_level == "high":
            await self.apply(fixed_code)
            return FixResult(success=True, confidence=score)
        else:
            # Zur Review queue
            await self.queue_for_review(fix, score)
            return FixResult(success=False, confidence=score)
```

### In der API

```python
@app.post("/api/v2/fix")
async def fix_endpoint(request: FixRequest):
    fix_result = await patch_loop.apply_fix(request.bug)
    
    return {
        "success": fix_result.success,
        "fix": fix_result.code,
        "confidence": fix_result.confidence.to_dict(),
        "auto_applied": fix_result.confidence.confidence_level == "high",
    }
```

## Best Practices

1. **Mindest-Score 70** für automatische Anwendung
2. **Immer erklären** warum ein Score niedrig ist
3. **Warnings** ernst nehmen und beheben
4. **Recommendations** als Aufgabenliste verwenden
5. **Tracking** über Zeit für Modell-Verbesserung

## Troubleshooting

### Niedriger Score trotz gutem Fix

Prüfe einzelne Faktoren:
```python
score = calculator.calculate(...)
for factor, value in score.factors.items():
    if value < 80:
        print(f"Problem: {factor.value} = {value}")
```

### Tests werden nicht erkannt

Stelle sicher dass Test-Ergebnisse übergeben werden:
```python
test_results = {
    "total": pytest_results.total,
    "passed": pytest_results.passed,
    "failed": pytest_results.failed,
}
score = calculator.calculate(..., test_results=test_results)
```