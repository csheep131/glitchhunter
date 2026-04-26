/**
 * GlitchHunter Web-UI - Refactoring Manager
 * 
 * Verwaltet Refactoring-Operationen:
 * - Dateien analysieren
 * - Vorschläge anzeigen
 * - Preview mit Diff
 * - Anwenden/Rollback
 */

class RefactoringManager {
    constructor() {
        this.currentSuggestions = [];
        this.currentPreview = null;
        this.apiBase = '/api/v1/refactor';
        
        this.init();
    }

    /**
     * Initialisiert Refactoring-Manager
     */
    init() {
        console.log('[Refactoring] Initialisiere...');
        
        // File-Select-Form
        document.getElementById('fileSelectForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            const filePath = document.getElementById('filePath').value;
            this.analyzeFile(filePath);
        });

        // Preview-Buttons
        document.getElementById('applyBtn')?.addEventListener('click', () => this.applyRefactoring());
        document.getElementById('cancelBtn')?.addEventListener('click', () => closePreview());

        // Projekte laden für File-Auswahl
        this.loadProjectFiles();

        console.log('[Refactoring] Initialisierung abgeschlossen');
    }

    async loadProjectFiles() {
        try {
            const res = await fetch('/api/v1/discover/projects');
            const data = await res.json();
            if (data.projects && data.projects.length > 0) {
                const datalist = document.getElementById('refactorFileList');
                if (datalist) {
                    datalist.innerHTML = data.projects.map(p =>
                        `<option value="${p}">${p.replace('/home/schaf/projects/', '')}</option>`
                    ).join('');
                    console.log(`[Refactoring] ${data.count} Projekte geladen`);
                }
            }
        } catch (error) {
            console.error('[Refactoring] Fehler beim Laden der Projektliste:', error);
        }
    }

    /**
     * Analysiert Datei auf Refactoring-Möglichkeiten
     */
    async analyzeFile(filePath) {
        try {
            console.log('[Refactoring] Analysiere Datei:', filePath);
            
            const response = await fetch(`${this.apiBase}/suggestions?file_path=${encodeURIComponent(filePath)}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const suggestions = await response.json();
            console.log('[Refactoring] Gefundene Vorschläge:', suggestions.length);

            this.currentSuggestions = suggestions;
            this.renderSuggestions(suggestions);

        } catch (error) {
            console.error('[Refactoring] Fehler beim Analysieren:', error);
            alert(`Fehler beim Analysieren: ${error.message}`);
        }
    }

    /**
     * Rendert Vorschlags-Liste
     */
    renderSuggestions(suggestions) {
        const list = document.getElementById('suggestionsList');
        const card = document.getElementById('suggestionsCard');
        
        if (!list || !card) return;

        if (!suggestions || suggestions.length === 0) {
            list.innerHTML = '<p style="text-align: center; color: #666; padding: 40px;">Keine Refactoring-Möglichkeiten gefunden</p>';
        } else {
            list.innerHTML = suggestions.map((s, i) => `
                <div class="suggestion-item ${s.risk_level}" onclick="refactoringManager.showPreview(${i})">
                    <div class="suggestion-header">
                        <span class="suggestion-title">${this.escapeHtml(s.title)}</span>
                        <span class="suggestion-badge badge-${s.risk_level}">${s.risk_level}</span>
                    </div>
                    <div class="suggestion-meta">
                        📁 ${this.escapeHtml(s.file_path)}:${s.line_start}-${s.line_end}
                        | 🎯 Konfidenz: ${(s.confidence * 100).toFixed(0)}%
                    </div>
                    <div class="suggestion-description">${this.escapeHtml(s.description)}</div>
                    <div class="suggestion-actions">
                        <button class="btn btn-small btn-primary" onclick="event.stopPropagation(); refactoringManager.showPreview(${i})">
                            👁️ Preview
                        </button>
                    </div>
                </div>
            `).join('');
        }

        card.style.display = 'block';
    }

    /**
     * Zeigt Preview für Vorschlag
     */
    async showPreview(index) {
        const suggestion = this.currentSuggestions[index];
        if (!suggestion) return;

        try {
            console.log('[Refactoring] Generiere Preview für:', suggestion.id);

            const response = await fetch(`${this.apiBase}/preview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(suggestion),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            this.currentPreview = await response.json();
            console.log('[Refactoring] Preview generiert:', this.currentPreview);

            // Modal füllen
            document.getElementById('previewTitle').textContent = suggestion.title;
            document.getElementById('previewFilePath').textContent = suggestion.file_path;
            
            const riskEl = document.getElementById('previewRisk');
            riskEl.textContent = this.currentPreview.risk_assessment;
            riskEl.className = `info-value risk-${suggestion.risk_level}`;
            
            document.getElementById('previewLinesAdded').textContent = this.currentPreview.lines_added;
            document.getElementById('previewLinesRemoved').textContent = this.currentPreview.lines_removed;
            
            const testsEl = document.getElementById('previewTestsRequired');
            testsEl.textContent = this.currentPreview.test_required ? '✅ Ja' : '❌ Nein';
            testsEl.style.color = this.currentPreview.test_required ? '#10b981' : '#666';

            // Diff rendern
            this.renderDiff(this.currentPreview.diff);

            // Modal anzeigen
            document.getElementById('previewModal').style.display = 'flex';

        } catch (error) {
            console.error('[Refactoring] Fehler beim Generieren der Preview:', error);
            alert(`Fehler beim Generieren der Preview: ${error.message}`);
        }
    }

    /**
     * Rendert Diff-Ansicht
     */
    renderDiff(diffText) {
        const diffView = document.getElementById('diffView');
        if (!diffView) return;

        const lines = diffText.split('\n');
        diffView.innerHTML = lines.map(line => {
            if (line.startsWith('+') && !line.startsWith('+++')) {
                return `<div class="diff-line diff-line-added">${this.escapeHtml(line)}</div>`;
            } else if (line.startsWith('-') && !line.startsWith('---')) {
                return `<div class="diff-line diff-line-removed">${this.escapeHtml(line)}</div>`;
            } else {
                return `<div class="diff-line diff-line-context">${this.escapeHtml(line)}</div>`;
            }
        }).join('');
    }

    /**
     * Wendet Refactoring an
     */
    async applyRefactoring() {
        if (!this.currentPreview) return;

        const btn = document.getElementById('applyBtn');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ Wende an...';

        try {
            console.log('[Refactoring] Wende Refactoring an...');

            const response = await fetch(`${this.apiBase}/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    suggestion_id: this.currentPreview.suggestion_id,
                    file_path: this.currentPreview.file_path,
                    preview_accepted: true,
                    create_backup: true,
                    run_tests: true,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('[Refactoring] Ergebnis:', result);

            // Status anzeigen
            const statusEl = document.getElementById('applyStatus');
            statusEl.style.display = 'block';
            
            if (result.success) {
                statusEl.textContent = `✅ ${result.message}`;
                statusEl.className = 'status-message success';
                
                // Modal nach 2 Sekunden schließen
                setTimeout(() => {
                    closePreview();
                    // Seite neu laden um aktualisierte Vorschläge zu sehen
                    location.reload();
                }, 2000);
            } else {
                statusEl.textContent = `❌ ${result.message}`;
                statusEl.className = 'status-message error';
            }

        } catch (error) {
            console.error('[Refactoring] Fehler beim Anwenden:', error);
            
            const statusEl = document.getElementById('applyStatus');
            statusEl.style.display = 'block';
            statusEl.textContent = `❌ Fehler: ${error.message}`;
            statusEl.className = 'status-message error';
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Globale Instanz
let refactoringManager;

// Modal-Funktionen
function closePreview() {
    document.getElementById('previewModal').style.display = 'none';
    document.getElementById('applyStatus').style.display = 'none';
}

// Modal bei Klick außerhalb schließen
window.onclick = function(event) {
    const modal = document.getElementById('previewModal');
    if (event.target === modal) {
        closePreview();
    }
}

// Initialisierung wenn DOM geladen ist
document.addEventListener('DOMContentLoaded', () => {
    refactoringManager = new RefactoringManager();
});
