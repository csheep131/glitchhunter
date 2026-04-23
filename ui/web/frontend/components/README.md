# GlitchHunter v3.0 - Dashboard Redesign Dokumentation

## Übersicht

Dieses Dokument beschreibt die Änderungen am GlitchHunter v3.0 Dashboard-Layout und die neue Component Library.

## Was wurde geändert?

### 1. Component Library erstellt

**Datei:** `ui/web/frontend/components/base.css`

Eine wiederverwendbare CSS-Komponentenbibliothek mit:

- **CSS Variables (Design Tokens):**
  - Farben: Sand (#d4c4a8), Gold (#c9b896), Grün (#10b981), Grau-Skala
  - Schatten: sm, md, lg, xl, glow
  - Border Radius: sm, md, lg, xl, 2xl, full
  - Spacing: 1-16 (4px bis 64px)
  - Icon Sizes: xs (16px) bis 3xl (128px)
  - Transitions: fast (150ms), base (200ms), slow (300ms)

- **Typography:**
  - System Fonts (-apple-system, BlinkMacSystemFont, Segoe UI, Roboto)
  - Headings h1-h6 mit konsistenter Größe
  - Utility Classes (.text-sm, .text-xs, .text-lg, .text-xl)

- **Buttons:**
  - `.btn` - Base Button
  - `.btn-primary` - Gradient (Sand/Gold)
  - `.btn-secondary` - Gray with border
  - `.btn-danger` - Red
  - `.btn-ghost` - Transparent
  - `.btn-sm`, `.btn-lg` - Size variants

- **Cards:**
  - `.card` - White card with shadow
  - `.card-header`, `.card-body`, `.card-footer` - Card sections
  - `.stat-card` - Special card for statistics with hover effect

- **Forms:**
  - `.form-group` - Form field wrapper
  - `.form-label` - Label styling
  - `.form-input`, `.form-select`, `.form-textarea` - Input styles
  - `.checkbox-grid` - Grid layout for checkboxes
  - `.checkbox-inline` - Inline checkbox with background
  - `.toggle` - Toggle switch component

- **Navigation:**
  - `.header` - Header container
  - `.header-brand` - Logo + title
  - `.header-nav` - Navigation links
  - `.nav-btn` - Navigation button
  - `.nav-icon` - 24x24px icon
  - `.mobile-nav-toggle` - Hamburger menu button

- **Layout:**
  - `.container` - Max-width 1200px, centered
  - `.grid`, `.grid-2`, `.grid-3`, `.grid-4` - Grid system
  - `.flex`, `.flex-col`, `.items-center`, etc. - Flexbox utilities

- **Responsive Breakpoints:**
  - Desktop: >1024px (4 columns)
  - Tablet: 768-1024px (2 columns)
  - Mobile: <768px (1 column, hamburger menu)
  - Small Mobile: <480px (smaller fonts)

### 2. Layout Template erstellt

**Datei:** `ui/web/frontend/components/layout.html`

Ein vollständiges Layout-Template mit Beispielen für:
- Header mit Logo und Navigation
- Mobile Navigation Toggle
- Stats Grid (4 Cards)
- Standard Card mit Header/Body/Footer
- Formular Card
- Buttons (alle Varianten)
- Badges & Status
- Alerts
- Progress Bar
- Grid System
- Footer

### 3. Alle HTML-Seiten aktualisiert

Folgende Seiten wurden mit dem neuen Design-System aktualisiert:

1. **index.html** (Haupt-Dashboard)
   - Navigation von 11 auf 6 Items reduziert
   - Mobile Navigation hinzugefügt
   - Stats Grid mit `.grid-4` Klasse
   - Formular mit `.form-input`, `.form-select`, `.checkbox-grid`
   - Footer mit Links zu OpenWebUI und API Docs

2. **problem.html** (Problemlöser)
   - Header mit Logo und Brand
   - Konsistente Navigation
   - Mobile Toggle

3. **refactor.html** (Refactoring)
   - Header mit Logo und Brand
   - Konsistente Navigation
   - Mobile Toggle

4. **reports.html** (Reports)
   - Header mit Logo und Brand
   - Konsistente Navigation
   - Mobile Toggle

5. **history.html** (History)
   - Header mit Logo und Brand
   - Konsistente Navigation
   - Mobile Toggle

6. **stacks.html** (Stack-Management)
   - Header mit Logo und Brand
   - Konsistente Navigation
   - Mobile Toggle

7. **models.html** (Model-Monitoring)
   - Header mit Logo und Brand
   - Konsistente Navigation
   - Mobile Toggle

8. **testing.html** (Stack-Testing)
   - Header mit Logo und Brand
   - Konsistente Navigation
   - Mobile Toggle

9. **hardware.html** (Hardware-Monitoring)
   - Header mit Logo und Brand
   - Konsistente Navigation
   - Mobile Toggle

10. **settings.html** (Einstellungen)
    - Header mit Logo und Brand
    - Konsistente Navigation
    - Mobile Toggle

## Navigation-Struktur

### Vorher (11 Items):
```
Dashboard | Problemlöser | Refactoring | Reports | History | Stacks | Models | Testing | Hardware | Einstellungen | OpenWebUI | API Docs
```

### Nachher (6 Haupt-Items + Footer):
```
Dashboard | Problemlöser | Refactoring | Reports | History | Einstellungen
```

**Sekundäre Links** (OpenWebUI, API Docs) wurden in den Footer verschoben.

## Wie verwende ich die Component Library?

### In einer neuen HTML-Seite:

```html
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meine Seite</title>
    <!-- Component Library laden -->
    <link rel="stylesheet" href="/static/components/base.css">
    <!-- Seiten-spezifische Styles (optional) -->
    <link rel="stylesheet" href="/static/meine-seite.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="header-content">
                <div class="header-brand">
                    <img src="/static/assets/logo_small.png" alt="Logo" class="header-logo">
                    <div>
                        <h1 class="header-title">Titel</h1>
                        <p class="header-subtitle">Untertitel</p>
                    </div>
                </div>
                <button class="mobile-nav-toggle" onclick="toggleMobileNav()">
                    <svg class="mobile-nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                    </svg>
                </button>
                <nav class="header-nav" id="mainNav">
                    <a href="/" class="nav-btn">Dashboard</a>
                    <!-- Weitere Nav-Items -->
                </nav>
            </div>
        </header>

        <!-- Content -->
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Card Titel</h2>
            </div>
            <div class="card-body">
                <!-- Content -->
            </div>
        </div>

        <!-- Footer -->
        <footer class="text-center text-muted text-sm py-6">
            <p>GlitchHunter v3.0</p>
        </footer>
    </div>

    <script>
        function toggleMobileNav() {
            document.getElementById('mainNav').classList.toggle('active');
        }
    </script>
</body>
</html>
```

### CSS Variables verwenden:

```css
.mein-element {
    color: var(--color-gold-dark);
    background: var(--bg-gradient);
    padding: var(--spacing-6);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-md);
    transition: all var(--transition-base);
}
```

### Grid System:

```html
<!-- 4 Spalten (Desktop), 2 (Tablet), 1 (Mobile) -->
<div class="grid grid-4">
    <div class="stat-card">...</div>
    <div class="stat-card">...</div>
    <div class="stat-card">...</div>
    <div class="stat-card">...</div>
</div>
```

### Formular:

```html
<form>
    <div class="form-group">
        <label class="form-label" for="input1">Label</label>
        <input type="text" id="input1" class="form-input" placeholder="...">
        <p class="form-help">Hilfetext</p>
    </div>
    
    <div class="form-group">
        <label class="form-label">Optionen</label>
        <div class="checkbox-grid">
            <label class="checkbox-inline">
                <input type="checkbox" checked>
                <span>Option 1</span>
            </label>
        </div>
    </div>
    
    <button type="submit" class="btn btn-primary btn-lg">Submit</button>
</form>
```

## Design-Prinzipien

### Nordic/Cyber Style
- **Farben:** Sand/Gold als Hauptfarben, Grün als Akzent
- **Typografie:** System Fonts (clean, modern, performant)
- **Layout:** Grid-basiert, ausgewogen, viel Whitespace
- **Icons:** Einheitliche Größen (24px Nav, 48px Stats)

### Responsive Design
- **Desktop First:** Standard für Desktop optimiert
- **Mobile-First Breakpoints:** Tablet (1024px), Mobile (768px), Small (480px)
- **Touch-freundlich:** Buttons mindestens 40px, große Touch-Targets
- **Hamburger Menu:** Auf Mobile automatisch aktiv

### Accessibility
- **ARIA Labels:** `aria-label` für Mobile Toggle
- **Kontrast:** Ausreichender Kontrast für Lesbarkeit
- **Focus States:** Sichtbare Focus-Indikatoren
- **Semantic HTML:** Correct use of header, nav, main, footer

## Dateien

### Neue Dateien:
- `ui/web/frontend/components/base.css` - Component Library
- `ui/web/frontend/components/layout.html` - Layout Template
- `ui/web/frontend/components/README.md` - Diese Dokumentation

### Geänderte Dateien:
- `ui/web/frontend/index.html` - Haupt-Dashboard
- `ui/web/frontend/problem.html` - Problemlöser
- `ui/web/frontend/refactor.html` - Refactoring
- `ui/web/frontend/reports.html` - Reports
- `ui/web/frontend/history.html` - History
- `ui/web/frontend/stacks.html` - Stack-Management
- `ui/web/frontend/models.html` - Model-Monitoring
- `ui/web/frontend/testing.html` - Stack-Testing
- `ui/web/frontend/hardware.html` - Hardware-Monitoring
- `ui/web/frontend/settings.html` - Einstellungen

### Unverändert (werden weiter verwendet):
- `ui/web/frontend/custom-graphics.css` - Grafik-spezifische Styles
- Alle `*.js` Dateien - JavaScript-Logik
- Alle anderen `*.css` Dateien - Seiten-spezifische Styles

## Nächste Schritte (Optional)

### P2 - Animationen/Transitions
- Page Transitions hinzufügen
- Loading States verbessern
- Hover-Effekte verfeinern

### P2 - Dark Mode Support
- CSS Variables für Dark Mode erweitern
- Toggle im Header hinzufügen
- `prefers-color-scheme` Media Query

### P2 - Accessibility
- ARIA Roles erweitern
- Keyboard Navigation verbessern
- Screen Reader Tests

## Support

Bei Fragen oder Problemen:
1. Layout Template (`components/layout.html`) als Referenz verwenden
2. CSS Variables in `base.css` durchsuchen
3. Bestehende Seiten als Beispiele ansehen

---

**GlitchHunter v3.0 • UI Redesign • April 2026**
