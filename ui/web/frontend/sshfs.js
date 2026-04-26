/**
 * GlitchHunter Web-UI - SSHFS Manager
 * 
 * Verwaltet SSHFS Remote-Mounts:
 * - Status abfragen
 * - Mount/Unmount
 * - Remote-Projekte auflisten
 * - Auto-Mount konfigurieren
 */

class SSHFSManager {
    constructor() {
        this.apiBase = '/api/v1/sshfs';
        this.mounted = false;
        this.statusData = null;

        // Nur initialisieren wenn SSHFS-Panel existiert (settings.html)
        if (document.getElementById('sshfs-panel')) {
            this.init();
        }
    }

    /**
     * Initialisiert SSHFS Manager
     */
    async init() {
        console.log('[SSHFS] Initialisiere...');
        await this.refreshStatus();
        console.log('[SSHFS] Initialisierung abgeschlossen');
    }

    /**
     * Aktualisiert den SSHFS-Status vom Backend
     */
    async refreshStatus() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            this.statusData = await response.json();
            this.mounted = this.statusData.mounted;
            this.updateUI();

            console.log(`[SSHFS] Status: ${this.mounted ? 'verbunden' : 'getrennt'}`, this.statusData);
        } catch (error) {
            console.error('[SSHFS] Fehler beim Status-Check:', error);
            this.showError(`Status-Check fehlgeschlagen: ${error.message}`);
        }
    }

    /**
     * Aktualisiert die UI-Elemente basierend auf dem Status
     */
    updateUI() {
        const data = this.statusData;
        if (!data) return;

        // Status-Badge
        const statusBadge = document.getElementById('sshfs-mount-status');
        if (statusBadge) {
            if (data.mounted) {
                statusBadge.textContent = '✅ Verbunden';
                statusBadge.className = 'model-status status-loaded';
            } else {
                statusBadge.textContent = '❌ Nicht verbunden';
                statusBadge.className = 'model-status status-error';
            }
        }

        // Info-Felder
        this.setElementText('sshfs-info-host', data.host || '–');
        this.setElementText('sshfs-info-remote', data.remote_path || '–');
        this.setElementText('sshfs-info-mount', data.mount_point || '–');
        this.setElementText('sshfs-info-projects', 
            data.mounted ? `${(data.projects || []).length} Projekte` : '–');

        // Formular-Felder aus Status befüllen (nur wenn nicht bereits vom User editiert)
        if (data.host) this.setInputElement('sshfs-host', data.host);
        if (data.remote_path) this.setInputElement('sshfs-remote-path', data.remote_path);
        if (data.mount_point) this.setInputElement('sshfs-mount-point', data.mount_point);
        if (data.host) this.setInputElement('sshfs-user', data.user || 'schaf');

        // Button-Zustände
        const mountBtn = document.getElementById('sshfs-mount-btn');
        const unmountBtn = document.getElementById('sshfs-unmount-btn');
        if (mountBtn) mountBtn.disabled = data.mounted;
        if (unmountBtn) unmountBtn.disabled = !data.mounted;

        // Projekte-Liste
        this.renderProjects(data.projects || []);

        // Fehler ausblenden wenn erfolgreich
        if (data.mounted) {
            this.hideError();
        } else if (data.error) {
            this.showError(data.error);
        }
    }

    /**
     * Mountet das Remote-Verzeichnis
     */
    async mount() {
        const config = {
            host: document.getElementById('sshfs-host')?.value || 'sundancer',
            user: document.getElementById('sshfs-user')?.value || 'schaf',
            remote_path: document.getElementById('sshfs-remote-path')?.value || '/home/schaf/projects',
            mount_point: document.getElementById('sshfs-mount-point')?.value || '/mnt/remote/projects',
            auto_mount: document.getElementById('sshfs-auto-mount')?.checked || false,
        };

        console.log('[SSHFS] Mount angefordert:', config);

        // Button deaktivieren (Loading-State)
        const mountBtn = document.getElementById('sshfs-mount-btn');
        if (mountBtn) {
            mountBtn.disabled = true;
            mountBtn.textContent = '⏳ Verbinde...';
        }

        try {
            const response = await fetch(`${this.apiBase}/mount`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            this.statusData = await response.json();
            this.mounted = this.statusData.mounted;
            this.updateUI();

            const projectCount = (this.statusData.projects || []).length;
            console.log(`[SSHFS] Mount erfolgreich: ${projectCount} Projekte sichtbar`);

        } catch (error) {
            console.error('[SSHFS] Mount fehlgeschlagen:', error);
            this.showError(`Mount fehlgeschlagen: ${error.message}`);
        } finally {
            if (mountBtn) {
                mountBtn.textContent = '🔗 Verbinden (Mount)';
                mountBtn.disabled = this.mounted;
            }
        }
    }

    /**
     * Unmountet das Remote-Verzeichnis
     */
    async unmount() {
        if (!confirm('Remote-Verzeichnis wirklich trennen?')) return;

        console.log('[SSHFS] Unmount angefordert');

        const unmountBtn = document.getElementById('sshfs-unmount-btn');
        if (unmountBtn) {
            unmountBtn.disabled = true;
            unmountBtn.textContent = '⏳ Trenne...';
        }

        try {
            const response = await fetch(`${this.apiBase}/unmount`, {
                method: 'POST',
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            this.statusData = await response.json();
            this.mounted = this.statusData.mounted;
            this.updateUI();

            console.log('[SSHFS] Unmount erfolgreich');

        } catch (error) {
            console.error('[SSHFS] Unmount fehlgeschlagen:', error);
            this.showError(`Unmount fehlgeschlagen: ${error.message}`);
        } finally {
            if (unmountBtn) {
                unmountBtn.textContent = '⛔ Trennen (Unmount)';
                unmountBtn.disabled = !this.mounted;
            }
        }
    }

    /**
     * Rendert die Remote-Projekte-Liste
     */
    renderProjects(projects) {
        const section = document.getElementById('sshfs-projects-section');
        const list = document.getElementById('sshfs-projects-list');

        if (!section || !list) return;

        if (!projects || projects.length === 0) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';

        list.innerHTML = projects.map(project => `
            <div class="model-card ${project.is_project ? '' : 'remote'}" style="cursor: pointer;"
                 onclick="sshfsManager.selectProject('${project.path}', '${project.name}')">
                <div class="model-header">
                    <span class="model-title">
                        ${project.is_project ? '📁' : '📂'} ${project.name}
                    </span>
                    ${project.is_project ? '<span class="model-status status-loaded">Git</span>' : ''}
                </div>
                <div class="model-info">
                    <div class="info-row">
                        <span class="info-label">Pfad:</span>
                        <span class="info-value" style="font-size: 0.85em; word-break: break-all;">${project.path}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Wählt ein Remote-Projekt für die Analyse aus
     */
    selectProject(path, name) {
        console.log(`[SSHFS] Projekt ausgewählt: ${name} (${path})`);
        
        // Zum Dashboard navigieren mit vorausgefülltem Pfad
        const url = `/?repo_path=${encodeURIComponent(path)}&source=sshfs`;
        window.location.href = url;
    }

    /**
     * Zeigt eine Fehlermeldung an
     */
    showError(message) {
        const errorEl = document.getElementById('sshfs-error');
        if (errorEl) {
            errorEl.textContent = `⚠️ ${message}`;
            errorEl.style.display = 'block';
        }
    }

    /**
     * Versteckt die Fehlermeldung
     */
    hideError() {
        const errorEl = document.getElementById('sshfs-error');
        if (errorEl) {
            errorEl.style.display = 'none';
        }
    }

    /**
     * Hilfsfunktion: Text in Element setzen
     */
    setElementText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    /**
     * Hilfsfunktion: Wert in Input-Element setzen
     */
    setInputElement(id, value) {
        const el = document.getElementById(id);
        if (el && !el.dataset.userEdited) el.value = value;
    }
}

// Globale Instanz
let sshfsManager;

// Initialisierung wenn DOM geladen
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('sshfs-panel')) {
        sshfsManager = new SSHFSManager();
        console.log('[SSHFS] SSHFSManager initialisiert');
    }
});