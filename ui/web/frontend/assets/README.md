# GlitchHunter v3.0 - Asset Dokumentation

## Übersicht

Dieses Dokument beschreibt die Grafik-Assets der GlitchHunter Web-UI im **Nordic Cyber Security** Design.

---

## Ordner-Struktur

```
ui/web/frontend/assets/
├── nav/              # Navigation Icons (128x128px)
├── status/           # Status Indicators (64x64px)
├── logo/             # Logo Varianten (64px/256px/512px)
├── decorative/       # Dekorative Elemente (Banner, Divider)
└── empty_states/     # Empty State Illustrationen (256x256px)
```

---

## Design-Philosophie

### Nordic Cyber Security

**Inspiration:** Norse Mythologie trifft Cyberpunk

**Farbpalette:**
- **Primary:** Sand/Gold (`#d4c4a8`, `#c9b896`)
- **Accent:** Neon-Grün (`#10b981`)
- **Dark:** Anthrazit (`#1f2937`)
- **Light:** Off-White (`#f9fafb`)

**Stil-Merkmale:**
- ✅ Symmetrische, geometrische Formen
- ✅ Metallische Texturen (Gold, Bronze)
- ✅ Neon-Akzente (Grün, Cyan)
- ✅ Runen/Circuit-Patterns als Details
- ✅ 3D-Tiefe durch Shadows/Gradients

---

## Asset-Kategorien

### 1. Navigation Icons (`/nav/`)

**Verwendung:** Hauptnavigation der Web-UI

| Icon | Datei | Größe | Beschreibung |
|------|-------|-------|--------------|
| 📊 Dashboard | `nav/dashboard.png` | 128×128px | Holografisches Control-Center |
| 🧠 Problemlöser | `nav/problem.png` | 128×128px | Neuronales Netzwerk |
| 🔧 Refactoring | `nav/refactor.png` | 128×128px | Goldene Werkzeuge |
| 📜 Reports | `nav/reports.png` | 128×128px | Holografische Runentafel |
| ⏳ History | `nav/history.png` | 128×128px | Nordische Sanduhr |
| 📚 Stacks | `nav/stacks.png` | 128×128px | Server-Rack |
| 🤖 Models | `nav/models.png` | 128×128px | Goldener Android |
| 🧪 Testing | `nav/testing.png` | 128×128px | Labor-Gefäß |
| 💻 Hardware | `nav/hardware.png` | 128×128px | Goldene GPU |
| ⚙️ Settings | `nav/settings.png` | 128×128px | Mechanisches Zahnrad |

**CSS-Klasse:** `.nav-icon`

```html
<a href="/" class="nav-btn">
    <img src="/static/assets/nav/dashboard.png" alt="" class="nav-icon">
    Dashboard
</a>
```

---

### 2. Status Icons (`/status/`)

**Verwendung:** Status-Anzeigen (Online/Offline/Error/Warning)

| Status | Datei | Größe | Animation |
|--------|-------|-------|-----------|
| 🟢 Online | `status/online.png` | 64×64px | Pulsierend (2s) |
| ⚫ Offline | `status/offline.png` | 64×64px | Keine |
| 🔴 Error | `status/error.png` | 64×64px | Pulsierend (1.5s) |
| 🟠 Warning | `status/warning.png` | 64×64px | Blinkend (1s) |

**CSS-Klasse:** `.status-icon`

```html
<span class="status-badge status-running">
    <img src="/static/assets/status/running.png" alt="" class="status-icon">
    Läuft
</span>
```

---

### 3. Logo Varianten (`/logo/`)

**Verwendung:** Branding an verschiedenen Stellen

| Variante | Datei | Größe | Verwendung |
|----------|-------|-------|------------|
| Favicon | `logo/logo_favicon.png` | 64×64px | Browser-Tab |
| Header | `logo/logo_256.png` | 256×256px | Seiten-Header |
| Hero | `logo/logo_512.png` | 512×512px | Landing Page |

**CSS-Klassen:** `.logo-small`, `.logo-medium`, `.logo-large`

```html
<!-- Header Logo -->
<div class="header-brand">
    <img src="/static/assets/logo/logo_256.png" alt="GlitchHunter" class="logo-small">
    <h1>GlitchHunter v3.0</h1>
</div>
```

---

### 4. Dashboard Banner (`/decorative/`)

**Verwendung:** Visuelle Aufwertung von Sections

| Element | Datei | Größe | Verwendung |
|---------|-------|-------|------------|
| Yggdrasil | `decorative/yggdrasil_banner.png` | 1200×300px | Dashboard Header |
| Bifrost | `decorative/bifrost_divider.png` | 800×100px | Section-Trenner |

**CSS-Klassen:** `.yggdrasil-banner`, `.bifrost-divider`

```html
<!-- Dashboard Banner -->
<img src="/static/assets/decorative/yggdrasil_banner.png" 
     alt="Yggdrasil" 
     class="yggdrasil-banner">

<!-- Section Divider -->
<img src="/static/assets/decorative/bifrost_divider.png" 
     alt="Bifrost" 
     class="bifrost-divider">
```

---

### 5. Empty States (`/empty_states/`)

**Verwendung:** Visuelle Darstellung von leeren Zuständen

| Zustand | Datei | Größe | Verwendung |
|---------|-------|-------|------------|
| Leer | `empty_states/empty_box.png` | 256×256px | Leere Listen |
| Suche | `empty_states/empty_search.png` | 256×256px | Keine Suchergebnisse |
| Daten | `empty_states/empty_data.png` | 256×256px | Leere Datenbank |

**CSS-Klasse:** `.empty-state-image`

```html
<div class="empty-state">
    <img src="/static/assets/empty_states/empty_box.png" 
         alt="Leer" 
         class="empty-state-image">
    <p>Keine Elemente vorhanden</p>
</div>
```

---

## CSS-Einbindung

### Basis-CSS

```html
<head>
    <!-- Design System -->
    <link rel="stylesheet" href="/static/components/base.css">
    
    <!-- Icon System -->
    <link rel="stylesheet" href="/static/components/icons.css">
</head>
```

### Wichtige CSS-Klassen

```css
/* Icon-Größen */
.icon-xs    /* 16×16px */
.icon-sm    /* 20×20px */
.icon-md    /* 24×24px */
.icon-lg    /* 32×32px */
.icon-xl    /* 48×48px */
.icon-2xl   /* 64×64px */
.icon-3xl   /* 128×128px */

/* Spezial-Klassen */
.nav-icon           /* Navigation (24×24px) */
.status-icon        /* Status (16×16px, animiert) */
.loading-spinner    /* Lade-Animation */
.empty-state-image  /* Empty States */
```

---

## Generierung

### Skript ausführen

```bash
# V2 Generator starten
python scripts/generate_webui_graphics_v2.py
```

### Voraussetzungen

- **ComfyUI** auf `http://asgard:8188`
- **SSH-Zugriff** auf Asgard für Bild-Download
- **ImageMagick** für Upscaling (optional)

### Prompt-Struktur

Jeder Prompt folgt diesem Schema:

```
flat geometric [OBJECT] icon, symmetrical [STYLE] design,
metallic [MATERIAL] ([COLOR] finish),
neon [ACCENT] glow,
[DETAILS] patterns,
clean minimal UI icon, transparent background,
professional interface asset, high detail, 1:1 aspect ratio
```

**Beispiel:**
```
flat geometric dashboard icon, symmetrical control panel design,
metallic gold gradient background (#c9b896 to #d4c4a8),
neon green holographic display screens (#10b981 glow),
subtle runic circuit patterns along edges,
clean minimal UI icon, transparent background,
professional interface asset, high detail, 1:1 aspect ratio
```

---

## Qualitäts-Check

### Automatische Prüfung

Das Generierungsskript prüft:

1. **Mindestgröße:** ≥5KB (vermeidet unscharfe Bilder)
2. **Upscaling:** Automatisch 2x für Retina-Displays
3. **Ordner:** Korrekte Zuordnung zu Kategorien

### Manuelle Prüfung

- [ ] Icons sind bei 100% Zoom scharf
- [ ] Farben entsprechen Design-Tokens
- [ ] Transparenter Hintergrund (kein Weiß)
- [ ] Hover-Effekte funktionieren
- [ ] Animationen laufen smooth

---

## Best Practices

### Do's ✅

- **CSS-Klassen verwenden** für konsistente Größen
- **Alt-Texte** für Accessibility (außer bei dekorativen Icons)
- **Hover-States** für Interaktion nutzen
- **Lazy Loading** für große Banner

### Don'ts ❌

- **Niemals inline-Styles** für Icon-Größen
- **Keine SVGs durch PNGs ersetzen** (wenn SVG verfügbar)
- **Nicht zu viele Animationen** gleichzeitig
- **Keine großen Bilder** ohne Optimierung

---

## Performance-Optimierung

### Bildgrößen

| Kategorie | Max. Größe | Format |
|-----------|-----------|--------|
| Nav Icons | <20KB | PNG |
| Status | <10KB | PNG |
| Logo | <50KB | PNG |
| Banner | <200KB | PNG |
| Empty States | <50KB | PNG |

### Lazy Loading

```html
<img src="/static/assets/decorative/yggdrasil_banner.png" 
     alt="Yggdrasil" 
     loading="lazy"
     class="yggdrasil-banner">
```

### WebP-Alternative (optional)

```html
<picture>
    <source srcset="/static/assets/nav/dashboard.webp" type="image/webp">
    <img src="/static/assets/nav/dashboard.png" alt="" class="nav-icon">
</picture>
```

---

## Accessibility

### ARIA-Labels

```html
<!-- Dekorative Icons (leer) -->
<img src="/static/assets/nav/dashboard.png" alt="" class="nav-icon">

<!-- Funktionale Icons -->
<img src="/static/assets/status/online.png" 
     alt="Online" 
     class="status-icon"
     aria-label="Status: Online">
```

### Reduced Motion

Das CSS berücksichtigt `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
    .icon, .loading-spinner, .status-icon {
        animation: none;
        transition: none;
    }
}
```

---

## Version History

### v2.0 (Aktuell)

- ✅ 128×128px Navigation Icons (Retina-ready)
- ✅ Spezifischere Prompts mit metallischen Texturen
- ✅ Ordner-Struktur für bessere Organisation
- ✅ Qualitäts-Check (Unschärfe-Erkennung)
- ✅ Automatisches Upscaling (2x)
- ✅ Umfassendes Icon-CSS mit Animationen

### v1.0 (Legacy)

- ❌ 64×64px Icons (zu klein für Retina)
- ❌ Generische Prompts
- ❌ Alle Assets in einem Ordner
- ❌ Kein Qualitäts-Check

---

## Support

**Fragen?** Siehe Dokumentation:

- [Design System](../../docs/design-system.md)
- [Component Library](../components/README.md)
- [Grafik-Generierung](../../docs/graphics-generation.md)

**Issues:** [GitHub Issues](https://github.com/glitchhunter/glitchhunter/issues)

---

*Zuletzt aktualisiert: 22. April 2026*
