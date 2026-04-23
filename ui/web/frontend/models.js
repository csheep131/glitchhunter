/**
 * GlitchHunter Web-UI - Model-Monitoring Manager
 * 
 * Verwaltet Model-Monitoring:
 * - Modell-Übersicht
 * - Status-Anzeige
 * - Load/Unload
 * - Health-Checks
 */

class ModelsManager {
    constructor() {
        this.apiBase = '/api/v1/models';
        
        this.init();
    }

    init() {
        console.log('[Models] Initialisiere...');
        
        // Tab-Handler
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Initiale Ladung
        this.loadStatistics();
        this.loadLocalModels();
        this.loadRemoteModels();
        
        // Alle 30s aktualisieren
        setInterval(() => {
            this.loadLocalModels();
            this.loadRemoteModels();
            this.loadStatistics();
        }, 30000);
    }

    switchTab(tabId) {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabId}-content`);
        });
    }

    async loadStatistics() {
        try {
            const response = await fetch(`${this.apiBase}/statistics`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const stats = await response.json();
            
            document.getElementById('statTotalLocal').textContent = stats.total_local;
            document.getElementById('statTotalRemote').textContent = stats.total_remote;
            document.getElementById('statLoaded').textContent = stats.local_loaded + stats.remote_available;
            document.getElementById('statVram').textContent = `${Math.round(stats.total_vram_usage_mb)} MB`;

        } catch (error) {
            console.error('[Models] Fehler beim Laden der Statistiken:', error);
        }
    }

    async loadLocalModels() {
        try {
            const response = await fetch(`${this.apiBase}/local`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const models = await response.json();
            this.renderLocalModels(models);

        } catch (error) {
            console.error('[Models] Fehler beim Laden der lokalen Modelle:', error);
        }
    }

    async loadRemoteModels() {
        try {
            const response = await fetch(`${this.apiBase}/remote`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const models = await response.json();
            this.renderRemoteModels(models);

        } catch (error) {
            console.error('[Models] Fehler beim Laden der Remote-Modelle:', error);
        }
    }

    renderLocalModels(models) {
        const list = document.getElementById('localModelsList');
        if (!list) return;

        if (!models || models.length === 0) {
            list.innerHTML = '<div class="empty-state">Keine lokalen Modelle gefunden</div>';
            return;
        }

        list.innerHTML = models.map(model => `
            <div class="model-card ${model.loaded ? 'loaded' : ''}">
                <div class="model-header">
                    <span class="model-title">📦 ${model.name}</span>
                    <span class="model-status status-${model.loaded ? 'loaded' : 'unloaded'}">
                        ${model.loaded ? 'Geladen' : 'Entladen'}
                    </span>
                </div>
                <div class="model-info">
                    <div class="info-row">
                        <span class="info-label">Größe:</span>
                        <span class="info-value">${Math.round(model.size_mb)} MB</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Quantisierung:</span>
                        <span class="info-value">${model.quantization}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">VRAM:</span>
                        <span class="info-value">${model.loaded ? Math.round(model.vram_usage_mb) : 0} MB</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Ladevorgänge:</span>
                        <span class="info-value">${model.load_count}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Ø Inferenz:</span>
                        <span class="info-value">${model.avg_inference_time_ms.toFixed(1)} ms</span>
                    </div>
                </div>
                <div class="model-actions">
                    ${model.loaded ? `
                        <button class="btn btn-secondary" onclick="modelsManager.unloadModel('${model.id}')">
                            ⏏️ Entladen
                        </button>
                    ` : `
                        <button class="btn btn-primary" onclick="modelsManager.loadModel('${model.id}')">
                            ⬇️ Laden
                        </button>
                    `}
                    <button class="btn btn-secondary" onclick="modelsManager.checkHealth('${model.id}')">
                        🏥 Health-Check
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderRemoteModels(models) {
        const list = document.getElementById('remoteModelsList');
        if (!list) return;

        if (!models || models.length === 0) {
            list.innerHTML = '<div class="empty-state">Keine Remote-Modelle gefunden</div>';
            return;
        }

        list.innerHTML = models.map(model => `
            <div class="model-card remote">
                <div class="model-header">
                    <span class="model-title">☁️ ${model.name}</span>
                    <span class="model-status status-${model.availability > 50 ? 'loaded' : 'error'}">
                        ${model.availability > 50 ? 'Verfügbar' : 'Nicht verfügbar'}
                    </span>
                </div>
                <div class="model-info">
                    <div class="info-row">
                        <span class="info-label">Provider:</span>
                        <span class="info-value">${model.provider}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">API:</span>
                        <span class="info-value">${model.api_url}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Rate-Limit:</span>
                        <span class="info-value">${model.rate_limit_per_minute}/min</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Requests heute:</span>
                        <span class="info-value">${model.requests_today}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Ø Latenz:</span>
                        <span class="info-value">${model.avg_latency_ms.toFixed(0)} ms</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Verfügbarkeit:</span>
                        <span class="info-value">${model.availability.toFixed(0)}%</span>
                    </div>
                </div>
                <div class="model-actions">
                    <button class="btn btn-secondary" onclick="modelsManager.checkHealth('${model.id}')">
                        🏥 Health-Check
                    </button>
                </div>
            </div>
        `).join('');
    }

    async loadModel(modelId) {
        try {
            console.log('[Models] Lade Modell:', modelId);
            
            const response = await fetch(`${this.apiBase}/load`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_id: modelId }),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const result = await response.json();
            
            if (result.success) {
                alert(`✅ ${result.message}`);
                this.loadLocalModels();
                this.loadStatistics();
            } else {
                alert(`❌ ${result.message}`);
            }

        } catch (error) {
            console.error('[Models] Fehler beim Laden:', error);
            alert(`Fehler beim Laden: ${error.message}`);
        }
    }

    async unloadModel(modelId) {
        try {
            console.log('[Models] Entlade Modell:', modelId);
            
            const response = await fetch(`${this.apiBase}/unload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_id: modelId }),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const result = await response.json();
            
            if (result.success) {
                alert(`✅ ${result.message}`);
                this.loadLocalModels();
                this.loadStatistics();
            } else {
                alert(`❌ ${result.message}`);
            }

        } catch (error) {
            console.error('[Models] Fehler beim Entladen:', error);
            alert(`Fehler beim Entladen: ${error.message}`);
        }
    }

    async checkHealth(modelId) {
        try {
            console.log('[Models] Health-Check für:', modelId);
            
            const response = await fetch(`${this.apiBase}/${modelId}/health`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const result = await response.json();
            
            let message = `Status: ${result.status}\n\n`;
            if (result.details) {
                message += Object.entries(result.details)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join('\n');
            }
            
            alert(`🏥 Health-Check für ${modelId}\n\n${message}`);

        } catch (error) {
            console.error('[Models] Fehler beim Health-Check:', error);
            alert(`Fehler beim Health-Check: ${error.message}`);
        }
    }

    async loadStatisticsDetail() {
        try {
            const response = await fetch(`${this.apiBase}/statistics`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const stats = await response.json();
            
            const content = document.getElementById('statisticsContent');
            content.innerHTML = `
                <div class="stat-row">
                    <span class="stat-row-label">Lokale Modelle (gesamt):</span>
                    <span class="stat-row-value">${stats.total_local}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-row-label">Lokale Modelle (geladen):</span>
                    <span class="stat-row-value">${stats.local_loaded}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-row-label">Remote-Modelle (gesamt):</span>
                    <span class="stat-row-value">${stats.total_remote}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-row-label">Remote-Modelle (verfügbar):</span>
                    <span class="stat-row-value">${stats.remote_available}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-row-label">VRAM-Nutzung (gesamt):</span>
                    <span class="stat-row-value">${Math.round(stats.total_vram_usage_mb)} MB</span>
                </div>
                <div class="stat-row">
                    <span class="stat-row-label">Ladevorgänge (gesamt):</span>
                    <span class="stat-row-value">${stats.total_load_count}</span>
                </div>
            `;

        } catch (error) {
            console.error('[Models] Fehler beim Laden der Statistiken:', error);
        }
    }
}

// Globale Instanz
let modelsManager;

// Initialisierung
document.addEventListener('DOMContentLoaded', () => {
    modelsManager = new ModelsManager();
});
