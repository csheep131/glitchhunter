# 🐛 GlitchHunter v3.0 - Grafik-Konzept V2

## Übersicht

Dieses Dokument beschreibt das **neue Grafik-Konzept** für die GlitchHunter Web-UI v3.0 im **Nordic Cyber Security** Design.

---

## 🎯 Probleme der V1-Lösung

| Problem | Auswirkung | Lösung in V2 |
|---------|-----------|--------------|
| **Grafiken zu klein** | 64×64px Icons zu detailarm für Retina | **128×128px** Navigation Icons |
| **Stil inkonsistent** | Manche wie Standard-Emoji | **Spezifische Prompts** mit Design-Tokens |
| **Prompt-Qualität** | Zu generisch | **Strukturierte Prompt-Vorlage** |
| **Einbindung umständlich** | CSS nicht optimal | **Icons.css** mit Animationen |
| **Keine Ordner-Struktur** | Alles in `/assets/` | **Kategorien:** nav/, status/, logo/, ... |
| **Kein Qualitäts-Check** | Unscharfe Bilder akzeptiert | **Automatische Prüfung** |

---

## 🎨 Design-Philosophie

### Nordic Cyber Security

**Inspiration:** Norse Mythologie trifft Cyberpunk

```
┌─────────────────────────────────────────────────────────────┐
│  🏛️ NORDIC           │  💻 CYBERPUNK                       │
├─────────────────────────────────────────────────────────────┤
│  Yggdrasil           │  Holographische Displays            │
│  Bifrost             │  Neon-Akzente (Grün, Cyan)          │
│  Runen               │  Circuit-Patterns                   │
│  Norse Götter        │  Androiden / KI                     │
│  Wikinger-Schiffe    │  Raumschiffe / Server               │
└─────────────────────────────────────────────────────────────┘
```

### Farbpalette

```css
--color-sand: #d4c4a8;      /* Primary */
--color-gold: #c9b896;      /* Metallic */
--color-green: #10b981;     /* Neon Accent */
--color-dark: #1f2937;      /* Dark Background */
--color-light: #f9fafb;     /* Light Background */
```

### Stil-Merkmale

- ✅ **Symmetrische, geometrische Formen**
- ✅ **Metallische Texturen** (Gold, Bronze)
- ✅ **Neon-Akzente** (Grün, Cyan)
- ✅ **Runen/Circuit-Patterns** als Details
- ✅ **3D-Tiefe** durch Shadows/Gradients

---

## 📁 Ordner-Struktur

```
ui/web/frontend/assets/
├── nav/              # Navigation Icons (128×128px)
│   ├── dashboard.png
│   ├── problem.png
│   ├── refactor.png
│   ├── reports.png
│   ├── history.png
│   ├── stacks.png
│   ├── models.png
│   ├── testing.png
│   ├── hardware.png
│   └── settings.png
│
├── status/           # Status Indicators (64×64px)
│   ├── online.png
│   ├── offline.png
│   ├── error.png
│   └── warning.png
│
├── logo/             # Logo Varianten
│   ├── logo_256.png  (256×256px)
│   ├── logo_512.png  (512×512px)
│   └── logo_favicon.png (64×64px)
│
├── decorative/       # Dekorative Elemente
│   ├── yggdrasil_banner.png (1200×300px)
│   ├── bifrost_divider.png (800×100px)
│   ├── circuit_board.png (512×512px)
│   └── runes_pattern.png (512×512px)
│
└── empty_states/     # Empty State Illustrationen (256×256px)
    ├── empty_box.png
    ├── empty_search.png
    └── empty_data.png
```

---

## 🛠️ Deliverables

### 1. Überarbeitete Prompts ✅

**Beispiel-Struktur:**

```python
"dashboard": {
    "prompt": (
        "flat geometric dashboard icon, symmetrical control panel design, "
        "metallic gold gradient background (#c9b896 to #d4c4a8), "
        "neon green holographic display screens (#10b981 glow), "
        "subtle runic circuit patterns along edges, "
        "clean minimal UI icon, transparent background, "
        "professional interface asset, high detail, 1:1 aspect ratio"
    ),
    "size": 128,
    "steps": 25,
    "folder": "nav"
}
```

**Qualitäts-Kriterien:**
- ✅ **Spezifisch:** Klare Beschreibung jedes Elements
- ✅ **Stil-konsistent:** Nordic Cyber durchgängig
- ✅ **Technisch:** Richtige Parameter für ComfyUI/Flux

---

### 2. Neues Generierungsskript ✅

**Datei:** `scripts/generate_webui_graphics_v2.py`

**Features:**
- ✅ Automatische Skalierung (128px → 256px/512px)
- ✅ Batch-Processing mit Fortschritt
- ✅ Qualitäts-Check (unscharfe Bilder erkennen)
- ✅ Ordner-Struktur (nav/, status/, decorative/, ...)
- ✅ Upscaling mit ImageMagick (optional)

**Ausführung:**
```bash
python scripts/generate_webui_graphics_v2.py
```

---

### 3. Icon-CSS ✅

**Datei:** `ui/web/frontend/components/icons.css`

**Features:**
- ✅ Icon-Größen (xs bis 3xl)
- ✅ Hover-Effekte mit Transform & Shadow
- ✅ Animationen (Loading, Status, Success/Error)
- ✅ Responsive Anpassungen
- ✅ Dark Mode Support
- ✅ Accessibility (Reduced Motion, High Contrast)

**Beispiel:**
```css
.nav-btn:hover .nav-icon {
    transform: scale(1.1) translateY(-2px);
    filter: drop-shadow(0 4px 8px rgba(212, 196, 168, 0.3));
}
```

---

### 4. Ordner-Struktur ✅

**Erstellt:**
```
ui/web/frontend/assets/
├── nav/              ✅
├── status/           ✅
├── logo/             ✅
├── decorative/       ✅
├── empty_states/     ✅
└── README.md         ✅
```

---

### 5. Migration ✅

**Skript:** `scripts/migrate_assets_v1_to_v2.py`

**Ergebnis:**
- ✅ 9/11 HTML-Dateien aktualisiert
- ✅ 63 Asset-Pfade migriert
- ✅ icons.css in allen Templates hinzugefügt

---

## 📋 Asset-Liste

### Navigation Icons (P0)

| Icon | Datei | Größe | Status |
|------|-------|-------|--------|
| 📊 Dashboard | `nav/dashboard.png` | 128×128px | ⏳ Ausstehend |
| 🧠 Problemlöser | `nav/problem.png` | 128×128px | ⏳ Ausstehend |
| 🔧 Refactoring | `nav/refactor.png` | 128×128px | ⏳ Ausstehend |
| 📜 Reports | `nav/reports.png` | 128×128px | ⏳ Ausstehend |
| ⏳ History | `nav/history.png` | 128×128px | ⏳ Ausstehend |
| 📚 Stacks | `nav/stacks.png` | 128×128px | ⏳ Ausstehend |
| 🤖 Models | `nav/models.png` | 128×128px | ⏳ Ausstehend |
| 🧪 Testing | `nav/testing.png` | 128×128px | ⏳ Ausstehend |
| 💻 Hardware | `nav/hardware.png` | 128×128px | ⏳ Ausstehend |
| ⚙️ Settings | `nav/settings.png` | 128×128px | ⏳ Ausstehend |

### Status Icons (P0)

| Icon | Datei | Größe | Status |
|------|-------|-------|--------|
| 🟢 Online | `status/online.png` | 64×64px | ⏳ Ausstehend |
| ⚫ Offline | `status/offline.png` | 64×64px | ⏳ Ausstehend |
| 🔴 Error | `status/error.png` | 64×64px | ⏳ Ausstehend |
| 🟠 Warning | `status/warning.png` | 64×64px | ⏳ Ausstehend |

### Logo Varianten (P0)

| Icon | Datei | Größe | Status |
|------|-------|-------|--------|
| Favicon | `logo/logo_favicon.png` | 64×64px | ⏳ Ausstehend |
| Header | `logo/logo_256.png` | 256×256px | ⏳ Ausstehend |
| Hero | `logo/logo_512.png` | 512×512px | ⏳ Ausstehend |

### Dashboard Banner (P1)

| Icon | Datei | Größe | Status |
|------|-------|-------|--------|
| Yggdrasil | `decorative/yggdrasil_banner.png` | 1200×300px | ⏳ Ausstehend |
| Bifrost | `decorative/bifrost_divider.png` | 800×100px | ⏳ Ausstehend |

### Empty States (P1)

| Icon | Datei | Größe | Status |
|------|-------|-------|--------|
| Leer | `empty_states/empty_box.png` | 256×256px | ⏳ Ausstehend |
| Suche | `empty_states/empty_search.png` | 256×256px | ⏳ Ausstehend |
| Daten | `empty_states/empty_data.png` | 256×256px | ⏳ Ausstehend |

---

## 🚀 Nächste Schritte

### P0 (Sofort - Generierung)

1. **ComfyUI Verbindung prüfen:**
   ```bash
   curl http://asgard:8188/system_stats
   ```

2. **Grafiken generieren:**
   ```bash
   cd /home/schaf/projects/glitchhunter
   python3 scripts/generate_webui_graphics_v2.py
   ```

3. **Qualitäts-Check:**
   - [ ] Alle Icons bei 100% Zoom scharf
   - [ ] Farben entsprechen Design-Tokens
   - [ ] Transparenter Hintergrund
   - [ ] Hover-Effekte funktionieren

### P1 (Danach - Integration)

4. **Yggdrasil Banner** ins Dashboard einfügen
5. **Empty States** in allen Listen verwenden
6. **Loading-Animationen** testen

### P2 (Optional - Erweiterung)

7. **WebP-Alternativen** generieren
8. **Dark Mode Varianten** erstellen
9. **Animation-Sprites** für Loading-States

---

## 📊 Performance-Ziele

| Metrik | Ziel | Aktuell |
|--------|------|---------|
| Nav Icon Größe | <20KB | - |
| Status Icon Größe | <10KB | - |
| Logo Größe | <50KB | - |
| Banner Größe | <200KB | - |
| Ladezeit (alle Icons) | <500ms | - |

---

## 🧪 Testing-Checkliste

### Visuelle Prüfung

- [ ] Icons sind bei 100% Zoom scharf
- [ ] Farben entsprechen Design-Tokens
- [ ] Transparenter Hintergrund (kein Weiß)
- [ ] Hover-Effekte funktionieren
- [ ] Animationen laufen smooth

### Funktionale Prüfung

- [ ] Navigation funktioniert auf allen Seiten
- [ ] Status-Icons zeigen korrekte Zustände
- [ ] Loading-Spinner dreht sich
- [ ] Empty States werden korrekt angezeigt

### Responsive Prüfung

- [ ] Desktop (1920×1080)
- [ ] Tablet (768×1024)
- [ ] Mobile (375×667)

### Accessibility Prüfung

- [ ] Alt-Texte vorhanden (wo nötig)
- [ ] Reduced Motion wird respektiert
- [ ] High Contrast Mode funktioniert

---

## 📚 Dokumentation

- [**Asset-README**](../ui/web/frontend/assets/README.md) - Detaillierte Asset-Doku
- [**Icons.css**](../ui/web/frontend/components/icons.css) - Icon-Styles
- [**Custom-Graphics.css**](../ui/web/frontend/custom-graphics.css) - Zusätzliche Styles
- [**Base.css**](../ui/web/frontend/components/base.css) - Design System

---

## 🔗 Links

- **ComfyUI:** http://asgard:8188
- **Dokumentation:** `/docs/`
- **Issues:** [GitHub](https://github.com/glitchhunter/glitchhunter/issues)

---

*Erstellt: 22. April 2026*  
*Version: 2.0*  
*Status: ✅ Konzept erstellt, ⏳ Generierung ausstehend*
