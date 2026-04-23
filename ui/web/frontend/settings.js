/**
 * GlitchHunter Web-UI - Settings Manager
 * 
 * Verwaltet die Einstellungen der Web-UI:
 * - Laden/Speichern von Settings
 * - Tab-Navigation
 * - Export/Import
 * - Validierung
 */

class SettingsManager {
    constructor() {
        this.currentTab = 'general';
        this.apiBase = '/api/v1/settings';
        
        this.init();
    }

    /**
     * Initialisiert Settings-Manager
     */
    async init() {
        console.log('[Settings] Initialisiere...');
        
        // Tab-Click-Handler
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Button-Handler
        document.getElementById('save-btn').addEventListener('click', () => this.saveAll());
        document.getElementById('reset-btn').addEventListener('click', () => this.reset());
        document.getElementById('export-btn').addEventListener('click', () => this.export());
        document.getElementById('import-btn').addEventListener('click', () => this.triggerImport());
        document.getElementById('import-file').addEventListener('change', (e) => this.import(e));

        // Settings laden
        await this.loadAll();
        
        console.log('[Settings] Initialisierung abgeschlossen');
    }

    /**
     * Wechselt Tab
     */
    switchTab(tabId) {
        console.log(`[Settings] Wechsle Tab: ${tabId}`);
        
        // Tabs aktualisieren
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        // Panels aktualisieren
        document.querySelectorAll('.settings-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `${tabId}-panel`);
        });

        this.currentTab = tabId;
    }

    /**
     * Lädt alle Settings
     */
    async loadAll() {
        try {
            console.log('[Settings] Lade alle Settings...');
            
            const response = await fetch(this.apiBase);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const settings = await response.json();
            console.log('[Settings] Geladene Settings:', settings);

            // Allgemein
            if (settings.general) {
                document.getElementById('language').value = settings.general.language || 'de';
                document.getElementById('theme').value = settings.general.theme || 'auto';
                document.getElementById('timezone').value = settings.general.timezone || 'Europe/Berlin';
                document.getElementById('date_format').value = settings.general.date_format || 'DD.MM.YYYY';
            }

            // Analyse
            if (settings.analysis) {
                document.getElementById('default_stack').value = settings.analysis.default_stack || 'stack_b';
                document.getElementById('default_parallel').checked = settings.analysis.default_parallel ?? true;
                document.getElementById('default_ml_prediction').checked = settings.analysis.default_ml_prediction ?? true;
                document.getElementById('default_auto_refactor').checked = settings.analysis.default_auto_refactor ?? false;
                document.getElementById('max_workers').value = settings.analysis.max_workers ?? 4;
                document.getElementById('timeout_per_analysis').value = settings.analysis.timeout_per_analysis ?? 300;
                document.getElementById('auto_refresh_interval').value = settings.analysis.auto_refresh_interval ?? 30;
            }

            // Security
            if (settings.security) {
                document.getElementById('session_timeout_minutes').value = settings.security.session_timeout_minutes ?? 60;
                document.getElementById('cors_origins').value = settings.security.cors_origins?.join('\n') || 'http://localhost:6262';
                document.getElementById('rate_limit_per_minute').value = settings.security.rate_limit_per_minute ?? 60;
            }

            // Logging
            if (settings.logging) {
                document.getElementById('logging_level').value = settings.logging.logging_level || 'INFO';
                document.getElementById('logging_file').value = settings.logging.logging_file || 'logs/glitchhunter_webui.log';
                document.getElementById('logging_max_size_mb').value = settings.logging.logging_max_size_mb ?? 10;
                document.getElementById('logging_backup_count').value = settings.logging.logging_backup_count ?? 5;
            }

            this.showMessage('Settings geladen', 'success');

        } catch (error) {
            console.error('[Settings] Fehler beim Laden:', error);
            this.showMessage(`Fehler beim Laden: ${error.message}`, 'error');
        }
    }

    /**
     * Speichert alle Settings
     */
    async saveAll() {
        try {
            console.log('[Settings] Speichere alle Settings...');

            const settings = {
                version: '1.0',
                general: {
                    language: document.getElementById('language').value,
                    theme: document.getElementById('theme').value,
                    timezone: document.getElementById('timezone').value,
                    date_format: document.getElementById('date_format').value,
                },
                analysis: {
                    default_stack: document.getElementById('default_stack').value,
                    default_parallel: document.getElementById('default_parallel').checked,
                    default_ml_prediction: document.getElementById('default_ml_prediction').checked,
                    default_auto_refactor: document.getElementById('default_auto_refactor').checked,
                    max_workers: parseInt(document.getElementById('max_workers').value),
                    timeout_per_analysis: parseInt(document.getElementById('timeout_per_analysis').value),
                    auto_refresh_interval: parseInt(document.getElementById('auto_refresh_interval').value),
                },
                security: {
                    session_timeout_minutes: parseInt(document.getElementById('session_timeout_minutes').value),
                    cors_origins: document.getElementById('cors_origins').value.split('\n').filter(line => line.trim()),
                    rate_limit_per_minute: parseInt(document.getElementById('rate_limit_per_minute').value),
                },
                logging: {
                    logging_level: document.getElementById('logging_level').value,
                    logging_file: document.getElementById('logging_file').value,
                    logging_max_size_mb: parseInt(document.getElementById('logging_max_size_mb').value),
                    logging_backup_count: parseInt(document.getElementById('logging_backup_count').value),
                },
            };

            console.log('[Settings] Zu speichernde Settings:', settings);

            const response = await fetch(this.apiBase, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Speichern fehlgeschlagen');
            }

            const result = await response.json();
            console.log('[Settings] Speichern erfolgreich:', result);

            this.showMessage(result.message || 'Settings gespeichert', 'success');

        } catch (error) {
            console.error('[Settings] Fehler beim Speichern:', error);
            this.showMessage(`Fehler beim Speichern: ${error.message}`, 'error');
        }
    }

    /**
     * Setzt Settings zurück
     */
    async reset() {
        if (!confirm('Möchten Sie wirklich alle Settings zurücksetzen?')) {
            return;
        }

        try {
            console.log('[Settings] Setze Settings zurück...');

            const response = await fetch(`${this.apiBase}/reset`, {
                method: 'POST',
            });

            if (!response.ok) {
                throw new Error('Zurücksetzen fehlgeschlagen');
            }

            await this.loadAll();
            this.showMessage('Settings zurückgesetzt', 'success');

        } catch (error) {
            console.error('[Settings] Fehler beim Zurücksetzen:', error);
            this.showMessage(`Fehler: ${error.message}`, 'error');
        }
    }

    /**
     * Exportiert Settings
     */
    async export() {
        try {
            console.log('[Settings] Exportiere Settings...');

            const response = await fetch(`${this.apiBase}/export`, {
                method: 'POST',
            });

            if (!response.ok) {
                throw new Error('Export fehlgeschlagen');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'glitchhunter-settings.json';
            a.click();
            window.URL.revokeObjectURL(url);

            console.log('[Settings] Export erfolgreich');
            this.showMessage('Settings exportiert', 'success');

        } catch (error) {
            console.error('[Settings] Fehler beim Export:', error);
            this.showMessage(`Fehler beim Export: ${error.message}`, 'error');
        }
    }

    /**
     * Trigger Import-Dialog
     */
    triggerImport() {
        document.getElementById('import-file').click();
    }

    /**
     * Importiert Settings aus Datei
     */
    async import(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            console.log('[Settings] Importiere Settings aus:', file.name);

            const text = await file.text();
            const settings = JSON.parse(text);

            const response = await fetch(`${this.apiBase}/import`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings),
            });

            if (!response.ok) {
                throw new Error('Import fehlgeschlagen');
            }

            await this.loadAll();
            console.log('[Settings] Import erfolgreich');
            this.showMessage('Settings importiert', 'success');

        } catch (error) {
            console.error('[Settings] Fehler beim Import:', error);
            this.showMessage(`Fehler beim Import: ${error.message}`, 'error');
        }

        // File-Input zurücksetzen
        event.target.value = '';
    }

    /**
     * Zeigt Status-Meldung
     */
    showMessage(message, type = 'success') {
        const el = document.getElementById('status-message');
        el.textContent = message;
        el.className = `status-message ${type}`;
        el.style.display = 'block';

        // Nach 3 Sekunden ausblenden
        setTimeout(() => {
            el.style.display = 'none';
        }, 3000);
    }
}

// Initialisierung wenn DOM geladen ist
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new SettingsManager();
});
