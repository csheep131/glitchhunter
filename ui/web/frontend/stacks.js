/**
 * GlitchHunter Web-UI - Stack-Manager
 * 
 * Verwaltet Stack-Management:
 * - Stack-Übersicht
 * - Konfiguration
 * - Testing
 */

class StacksManager {
    constructor() {
        this.apiBase = '/api/v1/stacks';
        this.currentStack = null;
        this.currentTest = null;
        
        this.init();
    }

    init() {
        console.log('[Stacks] Initialisiere...');
        this.loadStacks();
        this.updateStatuses();
        
        // Status alle 30s aktualisieren
        setInterval(() => this.updateStatuses(), 30000);
    }

    async loadStacks() {
        try {
            const response = await fetch(this.apiBase);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const stacks = await response.json();
            console.log('[Stacks] Geladene Stacks:', stacks.length);
            
            // Stacks rendern (wird zukünftig dynamisch sein)
            stacks.forEach(stack => {
                this.updateStackCard(stack);
            });

        } catch (error) {
            console.error('[Stacks] Fehler beim Laden:', error);
        }
    }

    updateStackCard(stack) {
        const card = document.querySelector(`[data-stack="${stack.id}"]`);
        if (!card) return;

        const statusEl = document.getElementById(`status_${stack.id}`);
        if (statusEl) {
            statusEl.textContent = stack.enabled ? 'Online' : 'Offline';
            statusEl.className = `stack-status status-${stack.enabled ? 'online' : 'offline'}`;
        }
    }

    async updateStatuses() {
        const stacks = ['stack_a', 'stack_b', 'stack_c'];
        
        for (const stackId of stacks) {
            try {
                const response = await fetch(`${this.apiBase}/${stackId}/status`);
                if (!response.ok) continue;
                
                const status = await response.json();
                const statusEl = document.getElementById(`status_${stackId}`);
                
                if (statusEl) {
                    statusEl.textContent = status.status === 'online' ? 'Online' : 
                                          status.status === 'error' ? 'Error' : 'Offline';
                    statusEl.className = `stack-status status-${status.status}`;
                }
                
            } catch (error) {
                console.error(`[Stacks] Fehler beim Status-Update für ${stackId}:`, error);
            }
        }
    }

    async showConfig(stackId) {
        try {
            console.log('[Stacks] Zeige Konfiguration für:', stackId);
            this.currentStack = stackId;

            const response = await fetch(`${this.apiBase}/${stackId}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const stack = await response.json();
            
            // Modal füllen
            document.getElementById('configTitle').textContent = `${stack.name} Konfiguration`;
            
            const form = document.getElementById('configForm');
            form.innerHTML = `
                <div class="form-group">
                    <label>Name:</label>
                    <input type="text" value="${stack.name}" readonly>
                </div>
                <div class="form-group">
                    <label>Hardware:</label>
                    <input type="text" value="${stack.hardware}" readonly>
                </div>
                <div class="form-group">
                    <label>Modus:</label>
                    <select id="configMode">
                        <option value="sequential" ${stack.mode === 'sequential' ? 'selected' : ''}>Sequenziell</option>
                        <option value="parallel" ${stack.mode === 'parallel' ? 'selected' : ''}>Parallel</option>
                        <option value="hybrid" ${stack.mode === 'hybrid' ? 'selected' : ''}>Hybrid</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Max Batch Size:</label>
                    <input type="number" id="configBatchSize" value="${stack.inference.max_batch_size || 4}" min="1" max="100">
                </div>
                <div class="form-group">
                    <label>Parallel Requests:</label>
                    <select id="configParallel">
                        <option value="true" ${stack.inference.parallel_requests ? 'selected' : ''}>Ja</option>
                        <option value="false" ${!stack.inference.parallel_requests ? 'selected' : ''}>Nein</option>
                    </select>
                </div>
            `;
            
            document.getElementById('configModal').style.display = 'flex';

        } catch (error) {
            console.error('[Stacks] Fehler beim Laden der Konfiguration:', error);
            alert(`Fehler: ${error.message}`);
        }
    }

    async saveConfig() {
        if (!this.currentStack) return;

        try {
            const updates = {
                mode: document.getElementById('configMode').value,
                inference: {
                    max_batch_size: parseInt(document.getElementById('configBatchSize').value),
                    parallel_requests: document.getElementById('configParallel').value === 'true',
                },
            };

            const response = await fetch(`${this.apiBase}/${this.currentStack}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            alert('✅ Konfiguration gespeichert!');
            closeConfig();
            this.loadStacks();

        } catch (error) {
            console.error('[Stacks] Fehler beim Speichern:', error);
            alert(`Fehler beim Speichern: ${error.message}`);
        }
    }

    async testStack(stackId, testType = 'quick') {
        try {
            console.log('[Stacks] Starte Test für:', stackId, testType);
            this.currentTest = stackId;

            // Modal anzeigen
            document.getElementById('testModal').style.display = 'flex';
            document.getElementById('testProgress').style.display = 'block';
            document.getElementById('testResults').style.display = 'none';
            document.getElementById('testProgressFill').style.width = '0%';

            // Fortschritts-Animation
            let progress = 0;
            const interval = setInterval(() => {
                progress += 5;
                document.getElementById('testProgressFill').style.width = `${Math.min(progress, 95)}%`;
            }, 500);

            const response = await fetch(`${this.apiBase}/${stackId}/test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ test_type: testType }),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const result = await response.json();
            
            clearInterval(interval);
            document.getElementById('testProgressFill').style.width = '100%';
            
            // Ergebnisse anzeigen
            setTimeout(() => {
                document.getElementById('testProgress').style.display = 'none';
                document.getElementById('testResults').style.display = 'block';
                
                const resultsDiv = document.getElementById('testResults');
                resultsDiv.innerHTML = `
                    <div class="result-row">
                        <span class="result-label">Test-ID:</span>
                        <span class="result-value">${result.test_id}</span>
                    </div>
                    <div class="result-row">
                        <span class="result-label">Typ:</span>
                        <span class="result-value">${result.test_type}</span>
                    </div>
                    <div class="result-row">
                        <span class="result-label">Status:</span>
                        <span class="result-value">${result.status}</span>
                    </div>
                    <div class="result-row">
                        <span class="result-label">Dauer:</span>
                        <span class="result-value">${result.duration_seconds.toFixed(2)}s</span>
                    </div>
                    ${Object.entries(result.results).map(([key, value]) => `
                        <div class="result-row">
                            <span class="result-label">${key}:</span>
                            <span class="result-value">${typeof value === 'number' ? value.toFixed(2) : value}</span>
                        </div>
                    `).join('')}
                    <div class="recommendation">
                        💡 ${result.recommendation}
                    </div>
                `;
            }, 500);

        } catch (error) {
            console.error('[Stacks] Fehler beim Testen:', error);
            alert(`Fehler beim Testen: ${error.message}`);
            closeTest();
        }
    }
}

// Globale Instanz
let stacksManager;

// Modal-Funktionen
function closeConfig() {
    document.getElementById('configModal').style.display = 'none';
}

function closeTest() {
    document.getElementById('testModal').style.display = 'none';
}

// Modal bei Klick außerhalb schließen
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Initialisierung
document.addEventListener('DOMContentLoaded', () => {
    stacksManager = new StacksManager();
});
