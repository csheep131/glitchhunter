# Caching & Incremental Scanning

GlitchHunter v2.0 implementiert ein leistungsfähiges Caching-System für blitzschnelle wiederholte Scans.

## Features

- **Symbol-Graph Cache**: Persistenter Disk-Cache für geparste Symbole
- **Incremental Scanner**: Trackt Datei-Änderungen, scannt nur Geändertes
- **LRU Eviction**: Automatische Bereinigung bei Größenlimit
- **TTL Support**: Zeitbasierte Invalidierung
- **Thread-Safe**: Parallele Zugriffe sicher

## Symbol-Graph Cache

### Übersicht

Der Symbol-Cache speichert geparste Symbol-Graphen auf Disk und vermeidet wiederholtes Parsen unveränderter Dateien.

```
~/.glitchhunter/cache/
├── cache.db              # SQLite Metadaten
├── ab/                   # Sharded Daten
│   ├── ab12cd34.pkl
│   └── ab56ef78.pkl
└── cd/
    └── cd90ab12.pkl
```

### Verwendung

```python
from src.cache import SymbolCache

# Cache initialisieren
cache = SymbolCache(
    cache_dir=Path.home() / ".glitchhunter" / "cache",
    max_size_mb=512,
    default_ttl_hours=168,  # 1 Woche
)

# Daten speichern
cache.set(
    file_path="/project/src/main.py",
    content=source_code,
    data=symbol_graph,
)

# Daten laden
cached = cache.get(
    file_path="/project/src/main.py",
    content=source_code,  # Hash-Vergleich
)

if cached:
    print("Cache-Hit!")
    symbol_graph = cached
else:
    print("Cache-Miss - parsen erforderlich")
    symbol_graph = parse_file(source_code)
    cache.set(...)
```

### Cache-Statistiken

```python
stats = cache.get_stats()
print(f"Hit Rate: {stats['hit_rate']:.1%}")
print(f"Entries: {stats['entry_count']}")
print(f"Size: {stats['total_size_mb']:.1f} MB")
```

### Cache verwalten

```python
# Einzelnen Eintrag invalidieren
cache.invalidate("/project/src/main.py")

# Cache komplett leeren
cache.invalidate_all()

# Automatische Cleanup
cache._maybe_evict()  # LRU bei Größenlimit
```

## Incremental Scanner

### Übersicht

Der Incremental Scanner trackt Datei-Zustände (mtime, size, content-hash) und identifiziert Änderungen seit dem letzten Scan.

### Verwendung

```python
from src.cache import IncrementalScanner

scanner = IncrementalScanner(
    project_path=Path("/project"),
)

# Alle Dateien
all_files = list(Path("/project").rglob("*.py"))

# Delta berechnen
to_scan, delta = scanner.get_files_to_scan(all_files)

print(f"Zu scannen: {len(to_scan)} von {len(all_files)} Dateien")
print(f"Neu: {len(delta.added)}")
print(f"Geändert: {len(delta.modified)}")
print(f"Gelöscht: {len(delta.deleted)}")
print(f"Unverändert: {len(delta.unchanged)}")

# Scan durchführen
for file_path in to_scan:
    result = scan_file(file_path)
    
    # Zustand aktualisieren
    scanner.update_state(file_path, result)
```

### ScanDelta Struktur

```python
@dataclass
class ScanDelta:
    added: List[str]        # Neue Dateien
    modified: List[str]     # Geänderte Dateien  
    deleted: List[str]      # Gelöschte Dateien
    unchanged: List[str]    # Unveränderte Dateien
    total_files: int
    incremental: bool       # True wenn inkrementell
```

### Git-Integration

```python
# Scan basierend auf Git-Commits
scanner = IncrementalScanner(project_path)

# Nur Dateien seit letztem Commit
changed_files = get_git_changed_files()
to_scan, delta = scanner.get_files_to_scan(changed_files)
```

### Force Full Scan

```python
# Alle Dateien scannen (kein Incremental)
to_scan, delta = scanner.get_files_to_scan(
    all_files,
    use_cache=False,  # Oder
)

# Oder über compute_delta
delta = scanner.compute_delta(all_files, force_full=True)
```

## Kombinierte Verwendung

### Optimaler Workflow

```python
from src.cache import SymbolCache, IncrementalScanner

class OptimizedScanner:
    def __init__(self, project_path):
        self.symbol_cache = SymbolCache()
        self.incremental = IncrementalScanner(project_path)
    
    async def scan_project(self, files: List[Path]):
        # 1. Incremental: Finde geänderte Dateien
        to_scan, delta = self.incremental.get_files_to_scan(files)
        
        results = []
        for file_path in to_scan:
            content = file_path.read_text()
            
            # 2. Symbol-Cache: Prüfe gecachte Graphen
            symbol_graph = self.symbol_cache.get(str(file_path), content)
            
            if symbol_graph is None:
                # 3. Parse und cache
                symbol_graph = await parse_symbols(content)
                self.symbol_cache.set(str(file_path), content, symbol_graph)
            
            # 4. Scan mit Symbol-Graph
            result = await security_scan(symbol_graph)
            results.append(result)
            
            # 5. Update Incremental-State
            self.incremental.update_state(file_path, result)
        
        return results, delta
```

### Performance-Vergleich

| Szenario | Ohne Cache | Mit Cache | Speedup |
|----------|-----------|-----------|---------|
| Erster Scan | 5:00 min | 5:00 min | 1x |
| Re-Scan (keine Änderungen) | 5:00 min | 0:05 min | **60x** |
| Re-Scan (10% geändert) | 5:00 min | 0:35 min | **8.5x** |
| Re-Scan (50% geändert) | 5:00 min | 2:30 min | **2x** |

## Konfiguration

### config.yaml

```yaml
cache:
  symbol_cache:
    enabled: true
    max_size_mb: 512
    ttl_hours: 168
    shard_size: 256  # Einträge pro Unterverzeichnis
  
  incremental_scan:
    enabled: true
    track_git_commits: true
    db_path: "~/.glitchhunter/incremental"
```

### Umgebungsvariablen

```bash
# Cache-Größe überschreiben
export GLITCHHUNTER_CACHE_SIZE_MB=1024

# Cache deaktivieren
export GLITCHHUNTER_DISABLE_CACHE=1

# Cache-Verzeichnis
export GLITCHHUNTER_CACHE_DIR=/mnt/fast_ssd/gh_cache
```

## CLI-Integration

### Automatisch

```bash
# Incremental wird automatisch verwendet
./scripts/run_auto.sh scan /path/to/repo

# Force full scan
./scripts/run_auto.sh scan --full /path/to/repo
```

### Manuelle Steuerung

```bash
# Cache-Status anzeigen
python -m src.cache info

# Cache leeren
python -m src.cache clear

# Cache-Größe anzeigen
du -sh ~/.glitchhunter/cache
```

## Troubleshooting

### Cache-Hit Rate zu niedrig

1. TTL erhöhen:
```yaml
cache:
  symbol_cache:
    ttl_hours: 336  # 2 Wochen
```

2. Cache-Größe erhöhen:
```yaml
cache:
  symbol_cache:
    max_size_mb: 1024
```

### Cache ist zu groß

1. Manuelle Bereinigung:
```python
cache = SymbolCache()
cache.invalidate_all()
```

2. Kleinere TTL:
```yaml
cache:
  symbol_cache:
    ttl_hours: 24
```

### Inkonsistenzen

1. Cache invalidieren wenn sich Parser ändert:
```python
# Nach Parser-Update
cache.invalidate_all()
```

2. Force full scan:
```bash
./scripts/run_auto.sh scan --full --clear-cache
```

## Best Practices

1. **Cache im Home-Verzeichnis**: Standard-Pfad verwenden
2. **Ausreichend TTL**: 1-2 Wochen für aktive Projekte
3. **Regelmäßige Cleanup**: LRU erledigt das automatisch
4. **Git-Hooks**: Cache invalidieren bei Branch-Wechsel
5. **CI/CD**: Cache persistieren zwischen Runs