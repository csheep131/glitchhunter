/**
 * GlitchHunter Web-UI - Stack-Konfiguration Manager
 * 
 * Verwaltet Stack-Konfiguration:
 * - Lokale Stacks (A/B)
 * - Remote-API (Stack C)
 * - Modell-Auswahl
 * - API-Verbindung testen
 */

class StackConfigManager {
    constructor() {
        this.apiBase = '/api/v1/stacks';
        this.currentStack = 'stack_a';
        this.availableModels = [];
        
        this.init();
    }

    init() {
        console.log('[StackConfig] Initialisiere...');

        // Tab-Handler - data-tab statt data-stack verwenden!
        document.querySelectorAll('.tab-btn').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchStack(e.target.dataset.tab));
        });

        // Initiale Ladung
        this.loadConfig('stack_a');
    }

    switchStack(stackId) {
        // Tabs aktualisieren - .tab-btn statt .stack-tab!
        document.querySelectorAll('.tab-btn').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === stackId);
        });

        // Config-Panels aktualisieren
        document.querySelectorAll('.stack-config').forEach(config => {
            config.classList.toggle('active', config.id === `${stackId}-config`);
        });

        this.currentStack = stackId;

        // Remote-Server laden wenn Tab gewechselt
        if (stackId === 'remote_servers' && typeof remoteServerManager !== 'undefined') {
            remoteServerManager.loadServers();
        } else {
            // Konfiguration laden
            this.loadConfig(stackId);
        }
    }

    async loadConfig(stackId) {
        try {
            const response = await fetch(`${this.apiBase}/${stackId}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const config = await response.json();
            
            if (stackId === 'stack_a') {
                document.getElementById('stack_a_mode').value = config.mode || 'sequential';
                document.getElementById('stack_a_primary').value = config.models?.primary || 'qwen3.5-9b-q4_k_m';
                document.getElementById('stack_a_secondary').value = config.models?.secondary || 'phi-4-mini-q8';
                document.getElementById('stack_a_batch').value = config.inference?.max_batch_size || 4;
                document.getElementById('stack_a_parallel').value = config.inference?.parallel_requests ? 'true' : 'false';
            }
            else if (stackId === 'stack_b') {
                document.getElementById('stack_b_mode').value = config.mode || 'parallel';
                document.getElementById('stack_b_primary').value = config.models?.primary || 'qwen3.5-27b-q4_k_m';
                document.getElementById('stack_b_secondary').value = config.models?.secondary || 'deepseek-v3.2-q8';
                document.getElementById('stack_b_batch').value = config.inference?.max_batch_size || 10;
                document.getElementById('stack_b_parallel').value = config.inference?.parallel_requests ? 'true' : 'false';
            }
            else if (stackId === 'stack_c') {
                // Remote-API Konfiguration
                const remoteConfig = config.remote || {};
                document.getElementById('stack_c_api_url').value = remoteConfig.api_url || 'http://asgard-llm:8081/v1';
                document.getElementById('stack_c_api_key').value = remoteConfig.api_key || 'asgard';
                document.getElementById('stack_c_api_type').value = remoteConfig.api_type || 'openai';
                document.getElementById('stack_c_timeout').value = remoteConfig.timeout || 120;
                document.getElementById('stack_c_rate_limit').value = remoteConfig.rate_limit || 60;
                document.getElementById('stack_c_batch').value = remoteConfig.max_batch_size || 10;
                document.getElementById('stack_c_parallel').value = remoteConfig.parallel_requests ? 'true' : 'false';
                
                // Modelle laden wenn vorhanden
                if (remoteConfig.available_models) {
                    this.availableModels = remoteConfig.available_models;
                    this.renderAvailableModels();
                    this.populateModelSelects();
                    
                    // Ausgewählte Modelle setzen
                    document.getElementById('stack_c_primary').value = remoteConfig.primary_model || '';
                    document.getElementById('stack_c_secondary').value = remoteConfig.secondary_model || '';
                }
            }

            console.log(`[StackConfig] Konfiguration geladen für ${stackId}`);

        } catch (error) {
            console.error(`[StackConfig] Fehler beim Laden von ${stackId}:`, error);
            alert(`Fehler beim Laden: ${error.message}`);
        }
    }

    async saveConfig(stackId) {
        try {
            let updates = {};

            if (stackId === 'stack_a') {
                updates = {
                    mode: document.getElementById('stack_a_mode').value,
                    models: {
                        primary: document.getElementById('stack_a_primary').value,
                        secondary: document.getElementById('stack_a_secondary').value,
                    },
                    inference: {
                        max_batch_size: parseInt(document.getElementById('stack_a_batch').value),
                        parallel_requests: document.getElementById('stack_a_parallel').value === 'true',
                    },
                };
            }
            else if (stackId === 'stack_b') {
                updates = {
                    mode: document.getElementById('stack_b_mode').value,
                    models: {
                        primary: document.getElementById('stack_b_primary').value,
                        secondary: document.getElementById('stack_b_secondary').value,
                    },
                    inference: {
                        max_batch_size: parseInt(document.getElementById('stack_b_batch').value),
                        parallel_requests: document.getElementById('stack_b_parallel').value === 'true',
                    },
                };
            }
            else if (stackId === 'stack_c') {
                updates = {
                    remote: {
                        api_url: document.getElementById('stack_c_api_url').value,
                        api_key: document.getElementById('stack_c_api_key').value,
                        api_type: document.getElementById('stack_c_api_type').value,
                        timeout: parseInt(document.getElementById('stack_c_timeout').value),
                        rate_limit: parseInt(document.getElementById('stack_c_rate_limit').value),
                        max_batch_size: parseInt(document.getElementById('stack_c_batch').value),
                        parallel_requests: document.getElementById('stack_c_parallel').value === 'true',
                        primary_model: document.getElementById('stack_c_primary').value,
                        secondary_model: document.getElementById('stack_c_secondary').value,
                        available_models: this.availableModels,
                    },
                };
            }

            const response = await fetch(`${this.apiBase}/${stackId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            alert(`✅ Konfiguration für ${stackId} gespeichert!`);
            console.log(`[StackConfig] Konfiguration gespeichert für ${stackId}`);

        } catch (error) {
            console.error(`[StackConfig] Fehler beim Speichern von ${stackId}:`, error);
            alert(`Fehler beim Speichern: ${error.message}`);
        }
    }

    async testConnection() {
        const apiUrl = document.getElementById('stack_c_api_url').value;
        const apiKey = document.getElementById('stack_c_api_key').value;
        const apiType = document.getElementById('stack_c_api_type').value;

        console.log('[StackConfig] Teste Verbindung zu:', apiUrl);

        try {
            const headers = {
                'Content-Type': 'application/json',
            };

            if (apiType === 'openai' || apiType === 'custom') {
                headers['Authorization'] = `Bearer ${apiKey}`;
            } else if (apiType === 'anthropic') {
                headers['x-api-key'] = apiKey;
                headers['anthropic-version'] = '2023-06-01';
            }

            let testUrl = apiUrl;
            if (apiType === 'ollama') {
                testUrl = apiUrl.replace('/v1', '') + '/api/tags';
            } else if (apiType === 'openai' || apiType === 'custom') {
                testUrl = apiUrl + '/models';
            }

            const response = await fetch(testUrl, { headers });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            alert('✅ Verbindung erfolgreich!\n\nAPI ist erreichbar und antwortet korrekt.');
            console.log('[StackConfig] Verbindungstest erfolgreich');

        } catch (error) {
            console.error('[StackConfig] Verbindungstest fehlgeschlagen:', error);
            alert(`❌ Verbindung fehlgeschlagen:\n\n${error.message}\n\nBitte überprüfen Sie:\n- API-Adresse\n- API-Key\n- Netzwerkverbindung\n- Firewall-Einstellungen`);
        }
    }

    async loadModels() {
        const apiUrl = document.getElementById('stack_c_api_url').value;
        const apiKey = document.getElementById('stack_c_api_key').value;
        const apiType = document.getElementById('stack_c_api_type').value;

        console.log('[StackConfig] Lade Modelle von:', apiUrl);

        try {
            const headers = {
                'Content-Type': 'application/json',
            };

            if (apiType === 'openai' || apiType === 'custom') {
                headers['Authorization'] = `Bearer ${apiKey}`;
            } else if (apiType === 'anthropic') {
                headers['x-api-key'] = apiKey;
                headers['anthropic-version'] = '2023-06-01';
            }

            let modelsUrl = apiUrl;
            if (apiType === 'ollama') {
                modelsUrl = apiUrl.replace('/v1', '') + '/api/tags';
            } else {
                modelsUrl = modelsUrl + '/models';
            }

            const response = await fetch(modelsUrl, { headers });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Modelle extrahieren (unterschiedliche Formate je nach API)
            if (apiType === 'ollama') {
                this.availableModels = data.models?.map(m => m.name) || [];
            } else {
                this.availableModels = data.data?.map(m => m.id) || [];
            }

            this.renderAvailableModels();
            this.populateModelSelects();

            alert(`✅ ${this.availableModels.length} Modelle geladen!`);
            console.log('[StackConfig] Modelle geladen:', this.availableModels);

        } catch (error) {
            console.error('[StackConfig] Fehler beim Laden der Modelle:', error);
            alert(`❌ Fehler beim Laden der Modelle:\n\n${error.message}`);
        }
    }

    renderAvailableModels() {
        const list = document.getElementById('availableModelsList');
        if (!list) return;

        if (this.availableModels.length === 0) {
            list.innerHTML = '<p class="placeholder-text">Keine Modelle gefunden</p>';
            return;
        }

        list.innerHTML = `
            <div class="models-grid">
                ${this.availableModels.map(model => `
                    <div class="model-badge">
                        📦 ${model}
                    </div>
                `).join('')}
            </div>
            <p class="help-text">${this.availableModels.length} Modelle verfügbar</p>
        `;
    }

    populateModelSelects() {
        const primarySelect = document.getElementById('stack_c_primary');
        const secondarySelect = document.getElementById('stack_c_secondary');

        if (!primarySelect || !secondarySelect) return;

        // Optionen speichern
        const primaryValue = primarySelect.value;
        const secondaryValue = secondarySelect.value;

        // Selects füllen
        primarySelect.innerHTML = '<option value="">-- Primäres Modell auswählen --</option>';
        secondarySelect.innerHTML = '<option value="">-- Sekundäres Modell auswählen --</option>';

        this.availableModels.forEach(model => {
            primarySelect.innerHTML += `<option value="${model}">${model}</option>`;
            secondarySelect.innerHTML += `<option value="${model}">${model}</option>`;
        });

        // Ausgewählte Werte wiederherstellen
        if (primaryValue) primarySelect.value = primaryValue;
        if (secondaryValue) secondarySelect.value = secondaryValue;
    }

    resetToDefault(stackId) {
        if (!confirm(`Möchten Sie die Konfiguration für ${stackId} wirklich auf Standard zurücksetzen?`)) {
            return;
        }

        // Standard-Werte setzen
        if (stackId === 'stack_c') {
            document.getElementById('stack_c_api_url').value = 'http://asgard-llm:8081/v1';
            document.getElementById('stack_c_api_key').value = 'asgard';
            document.getElementById('stack_c_api_type').value = 'openai';
            document.getElementById('stack_c_timeout').value = 120;
            document.getElementById('stack_c_rate_limit').value = 60;
            document.getElementById('stack_c_batch').value = 10;
            document.getElementById('stack_c_parallel').value = 'true';
            
            this.availableModels = [];
            this.renderAvailableModels();
            this.populateModelSelects();
        }

        alert(`✅ Konfiguration zurückgesetzt`);
    }
}

// Globale Instanz
let stackConfigManager;

// Initialisierung
document.addEventListener('DOMContentLoaded', () => {
    stackConfigManager = new StackConfigManager();
});
