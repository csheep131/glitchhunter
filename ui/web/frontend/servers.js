/**
 * GlitchHunter Web-UI - Remote-Server Manager
 * 
 * Verwaltet Remote-Server:
 * - Server hinzufügen/bearbeiten/löschen
 * - Server-Status prüfen
 * - Verfügbare Modelle laden
 */

class RemoteServerManager {
    constructor() {
        this.apiBase = '/api/v1/servers';
        this.currentServerId = null;
        
        // Initialisieren wenn Server-Tab vorhanden ist
        if (document.getElementById('servers-content') || document.getElementById('remote_servers-config')) {
            this.init();
        }
    }

    init() {
        console.log('[Servers] Initialisiere...');
        this.loadServers();
        
        // Alle 30s aktualisieren
        setInterval(() => this.loadServers(), 30000);
    }

    async loadServers() {
        try {
            const response = await fetch(`${this.apiBase}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const servers = await response.json();
            this.renderServers(servers);

        } catch (error) {
            console.error('[Servers] Fehler beim Laden:', error);
        }
    }

    renderServers(servers) {
        // Versuche beide Container-IDs
        const list = document.getElementById('serversList') || document.getElementById('remoteServersList');
        if (!list) return;

        if (!servers || servers.length === 0) {
            list.innerHTML = '<div class="empty-state">Keine Server konfiguriert</div>';
            return;
        }

        list.innerHTML = servers.map(server => `
            <div class="model-card remote">
                <div class="model-header">
                    <span class="model-title">${server.name}</span>
                    <span class="model-status status-${server.status === 'online' ? 'loaded' : 'error'}">
                        ${server.status}
                    </span>
                </div>
                <div class="model-info">
                    <div class="info-row">
                        <span class="info-label">Host:</span>
                        <span class="info-value">${server.host}:${server.port}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">API-Typ:</span>
                        <span class="info-value">${server.api_type}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Modelle:</span>
                        <span class="info-value">${server.available_models.length}</span>
                    </div>
                    ${server.last_checked ? `
                    <div class="info-row">
                        <span class="info-label">Geprüft:</span>
                        <span class="info-value">${new Date(server.last_checked).toLocaleTimeString('de-DE')}</span>
                    </div>
                    ` : ''}
                </div>
                <div class="model-actions">
                    ${server.api_type === 'openwebui' ? `
                    <button class="btn btn-primary" onclick="window.open('http://${server.host}:${server.port}', '_blank')">
                        💬 OpenWebUI öffnen
                    </button>
                    ` : `
                    <button class="btn btn-secondary" onclick="remoteServerManager.checkServer('${server.id}')">
                        🔄 Status prüfen
                    </button>
                    `}
                    <button class="btn btn-secondary" onclick="remoteServerManager.showEditServerModal('${server.id}')">
                        ⚙️ Bearbeiten
                    </button>
                    <button class="btn btn-secondary" onclick="remoteServerManager.deleteServer('${server.id}')">
                        🗑️ Löschen
                    </button>
                </div>
            </div>
        `).join('');
    }

    showAddServerModal() {
        this.currentServerId = null;
        document.getElementById('serverModalTitle').textContent = 'Server hinzufügen';
        document.getElementById('serverForm').reset();
        document.getElementById('serverModal').style.display = 'flex';
    }

    async showEditServerModal(serverId) {
        try {
            console.log('[Servers] Bearbeite Server:', serverId);
            this.currentServerId = serverId;
            
            const response = await fetch(`${this.apiBase}/${serverId}`);
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const server = await response.json();
            console.log('[Servers] Geladener Server:', server);
            
            document.getElementById('serverModalTitle').textContent = 'Server bearbeiten';
            document.getElementById('serverName').value = server.name || '';
            document.getElementById('serverHost').value = server.host || '';
            document.getElementById('serverPort').value = server.port || 11434;
            document.getElementById('serverApiType').value = server.api_type || 'ollama';
            document.getElementById('serverApiKey').value = server.api_key || '';
            
            document.getElementById('serverModal').style.display = 'flex';
            
        } catch (error) {
            console.error('[Servers] Fehler beim Laden:', error);
            alert(`Fehler beim Laden des Servers: ${error.message}\n\nStellen Sie sicher, dass der Server existiert und erreichbar ist.`);
        }
    }

    async saveServer() {
        const serverData = {
            name: document.getElementById('serverName').value,
            host: document.getElementById('serverHost').value,
            port: parseInt(document.getElementById('serverPort').value),
            api_type: document.getElementById('serverApiType').value,
            api_key: document.getElementById('serverApiKey').value,
            enabled: true,
        };

        console.log('[Servers] Speichere Server:', this.currentServerId, serverData);

        try {
            let url = this.apiBase;
            let method = 'POST';
            
            if (this.currentServerId) {
                // Existierenden Server aktualisieren
                url = `${this.apiBase}/${this.currentServerId}`;
                method = 'PUT';
            }
            
            console.log('[Servers] Request:', method, url, serverData);
            
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(serverData),
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log('[Servers] Antwort:', result);
            
            const action = this.currentServerId ? 'aktualisiert' : 'hinzugefügt';
            alert(`✅ Server ${action}`);
            
            // Modal schließen - Funktion ist global verfügbar
            if (typeof closeServerModal === 'function') {
                closeServerModal();
            } else {
                document.getElementById('serverModal').style.display = 'none';
            }
            
            this.loadServers();

        } catch (error) {
            console.error('[Servers] Fehler beim Speichern:', error);
            
            // Wenn Server existiert (400), trotzdem als Erfolg behandeln
            if (error.message.includes('400') && this.currentServerId) {
                alert(`⚠️ Server konnte nicht aktualisiert werden, existiert aber bereits.\n\n${error.message}`);
                closeServerModal();
                return;
            }
            
            alert(`Fehler beim Speichern: ${error.message}`);
        }
    }

    async checkServer(serverId) {
        try {
            console.log('[Servers] Prüfe Server:', serverId);
            
            const response = await fetch(`${this.apiBase}/${serverId}/check`, {
                method: 'POST',
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const result = await response.json();
            
            alert(`Server-Status: ${result.status}\n\nVerfügbare Modelle: ${result.available_models.length}\n${result.error_message || ''}`);
            this.loadServers();

        } catch (error) {
            console.error('[Servers] Fehler beim Status-Check:', error);
            alert(`Fehler: ${error.message}`);
        }
    }

    async deleteServer(serverId) {
        if (!confirm(`Möchten Sie den Server "${serverId}" wirklich löschen?\n\nDies kann nicht rückgängig gemacht werden.`)) {
            return;
        }

        console.log('[Servers] Lösche Server:', serverId);

        try {
            const response = await fetch(`${this.apiBase}/${serverId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log('[Servers] Gelöscht:', result);
            
            alert('✅ Server gelöscht');
            this.loadServers();

        } catch (error) {
            console.error('[Servers] Fehler beim Löschen:', error);
            alert(`Fehler beim Löschen: ${error.message}`);
        }
    }
}

// Globale Instanz
let remoteServerManager;

// Modal-Funktion - GLOBAL verfügbar für models.html und stack-config.html
function closeServerModal() {
    const modal = document.getElementById('serverModal');
    if (modal) {
        modal.style.display = 'none';
    }
    const form = document.getElementById('serverForm');
    if (form) {
        form.reset();
    }
}

// Initialisierung - sofort wenn DOM ready, oder nach DOMContentLoaded
function initRemoteServerManager() {
    if (typeof remoteServerManager === 'undefined') {
        remoteServerManager = new RemoteServerManager();
        console.log('[Servers] RemoteServerManager initialisiert');
    }
}

// Sofort initialisieren wenn Element existiert
if (document.getElementById('servers-content') || document.getElementById('remote_servers-config')) {
    initRemoteServerManager();
} else {
    // Sonst nach DOMContentLoaded
    document.addEventListener('DOMContentLoaded', initRemoteServerManager);
}
