/**
 * GlitchHunter Web-UI - Stack-Testing Manager
 * 
 * Verwaltet Stack-Testing:
 * - Tests starten
 * - Fortschritt anzeigen
 * - Ergebnisse anzeigen
 * - Historie laden
 */

class TestingManager {
    constructor() {
        this.apiBase = '/api/v1/stacks';
        this.currentTest = null;
        this.testInterval = null;
        
        this.init();
    }

    init() {
        console.log('[Testing] Initialisiere...');
        
        // Form-Handler
        document.getElementById('testForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.startTest();
        });

        // Filter-Handler
        document.getElementById('historyStackFilter')?.addEventListener('change', () => this.loadHistory());
        document.getElementById('historyTypeFilter')?.addEventListener('change', () => this.loadHistory());

        // Historie laden
        this.loadHistory();
    }

    async startTest() {
        const stackId = document.getElementById('stackSelect').value;
        const testType = document.getElementById('testTypeSelect').value;

        console.log('[Testing] Starte Test:', stackId, testType);

        try {
            // UI umschalten
            document.getElementById('testSelectionCard').style.display = 'none';
            document.getElementById('runningTestCard').style.display = 'block';
            document.getElementById('resultsCard').style.display = 'none';

            // Fortschritts-Anzeige initialisieren
            document.getElementById('runningStack').textContent = stackId.replace('stack_', 'Stack ');
            document.getElementById('runningType').textContent = this.getTestTypeName(testType);
            document.getElementById('testProgressFill').style.width = '0%';
            document.getElementById('testProgressText').textContent = 'Test initialisiert...';

            let duration = 0;
            this.testInterval = setInterval(() => {
                duration++;
                document.getElementById('runningDuration').textContent = `${duration}s`;
                
                // Fortschritt simulieren
                const progress = Math.min((duration / this.getTestDuration(testType)) * 100, 95);
                document.getElementById('testProgressFill').style.width = `${progress}%`;
                
                // Status-Updates
                if (duration === 5) {
                    document.getElementById('testProgressText').textContent = 'Modelle werden geladen...';
                } else if (duration === 15) {
                    document.getElementById('testProgressText').textContent = 'Führe Inference-Tests durch...';
                } else if (duration === 30) {
                    document.getElementById('testProgressText').textContent = 'Analysiere Ergebnisse...';
                }
            }, 1000);

            // Test-API aufrufen
            const response = await fetch(`${this.apiBase}/${stackId}/test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ test_type: testType }),
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const result = await response.json();
            
            clearInterval(this.testInterval);
            this.currentTest = result;

            // Test abgeschlossen
            this.showResults(result);

        } catch (error) {
            console.error('[Testing] Fehler beim Testen:', error);
            clearInterval(this.testInterval);
            alert(`Fehler beim Testen: ${error.message}`);
            this.resetUI();
        }
    }

    getTestTypeName(type) {
        const names = {
            'quick': 'Quick-Test',
            'performance': 'Performance-Test',
            'stress': 'Stress-Test',
        };
        return names[type] || type;
    }

    getTestDuration(type) {
        const durations = {
            'quick': 30,
            'performance': 180,
            'stress': 600,
        };
        return durations[type] || 30;
    }

    showResults(result) {
        console.log('[Testing] Test-Ergebnis:', result);

        document.getElementById('runningTestCard').style.display = 'none';
        document.getElementById('resultsCard').style.display = 'block';

        // Header
        document.getElementById('resultStatus').textContent = result.status === 'completed' ? '✅ Abgeschlossen' : '❌ Fehlgeschlagen';
        document.getElementById('resultStack').textContent = result.stack_id.replace('stack_', 'Stack ');
        document.getElementById('resultType').textContent = this.getTestTypeName(result.test_type);
        document.getElementById('resultDuration').textContent = `${result.duration_seconds.toFixed(1)}s`;

        // Metriken
        const metricsGrid = document.getElementById('metricsGrid');
        metricsGrid.innerHTML = Object.entries(result.results)
            .filter(([key]) => key !== 'success' && key !== 'message')
            .map(([key, value]) => `
                <div class="metric-card">
                    <div class="metric-label">${this.formatMetricLabel(key)}</div>
                    <div class="metric-value">${typeof value === 'number' ? value.toFixed(2) : value}</div>
                    <div class="metric-unit">${this.getMetricUnit(key)}</div>
                </div>
            `).join('');

        // Empfehlung
        document.getElementById('recommendationBox').textContent = result.recommendation;

        // Historie neu laden
        this.loadHistory();
    }

    formatMetricLabel(key) {
        const labels = {
            'avg_response_time_ms': 'Ø Antwortzeit',
            'p95_response_time_ms': 'P95 Antwortzeit',
            'p99_response_time_ms': 'P99 Antwortzeit',
            'requests_per_second': 'Requests/Sekunde',
            'total_requests': 'Gesamte Requests',
            'failed_requests': 'Fehlgeschlagene Requests',
            'success_rate': 'Erfolgsrate',
            'model_load_time_ms': 'Ladezeit Modell',
            'inference_time_ms': 'Inferenzzeit',
            'max_concurrent_requests': 'Max. gleichzeitige Requests',
            'memory_peak_mb': 'Speicher-Peak',
            'error_rate': 'Fehlerrate',
            'recovery_time_ms': 'Wiederherstellungszeit',
        };
        return labels[key] || key.replace(/_/g, ' ').toUpperCase();
    }

    getMetricUnit(key) {
        const units = {
            'avg_response_time_ms': 'ms',
            'p95_response_time_ms': 'ms',
            'p99_response_time_ms': 'ms',
            'requests_per_second': 'req/s',
            'model_load_time_ms': 'ms',
            'inference_time_ms': 'ms',
            'memory_peak_mb': 'MB',
            'recovery_time_ms': 'ms',
            'error_rate': '%',
            'success_rate': '%',
        };
        return units[key] || '';
    }

    async loadHistory() {
        try {
            const stackFilter = document.getElementById('historyStackFilter').value;
            const typeFilter = document.getElementById('historyTypeFilter').value;

            // Für Demo: Alle Stacks durchgehen
            const stacks = ['stack_a', 'stack_b', 'stack_c'];
            let allTests = [];

            for (const stack of stacks) {
                try {
                    const response = await fetch(`${this.apiBase}/${stack}/tests?limit=10`);
                    if (!response.ok) continue;
                    
                    const tests = await response.json();
                    allTests = [...allTests, ...tests];
                } catch (error) {
                    // Stack hat keine Tests
                }
            }

            // Filtern
            if (stackFilter) {
                allTests = allTests.filter(t => t.stack_id === stackFilter);
            }
            if (typeFilter) {
                allTests = allTests.filter(t => t.test_type === typeFilter);
            }

            // Sortieren (neueste zuerst)
            allTests.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

            this.renderHistory(allTests.slice(0, 20));

        } catch (error) {
            console.error('[Testing] Fehler beim Laden der Historie:', error);
        }
    }

    renderHistory(tests) {
        const list = document.getElementById('historyList');
        if (!list) return;

        if (!tests || tests.length === 0) {
            list.innerHTML = '<div class="empty-state">Keine Tests gefunden</div>';
            return;
        }

        list.innerHTML = tests.map(test => `
            <div class="history-item ${test.test_type}" onclick="testingManager.showTestResult('${test.test_id}')">
                <div class="history-header">
                    <span class="history-title">
                        ${test.stack_id.replace('stack_', 'Stack ')} - ${this.getTestTypeName(test.test_type)}
                    </span>
                    <span class="history-type type-${test.test_type}">${test.test_type}</span>
                </div>
                <div class="history-meta">
                    <span>🕐 ${new Date(test.created_at).toLocaleString('de-DE')}</span>
                    <span>⏱️ ${test.duration_seconds.toFixed(1)}s</span>
                    <span>${test.status === 'completed' ? '✅' : '❌'} ${test.status}</span>
                </div>
            </div>
        `).join('');
    }

    async showTestResult(testId) {
        alert(`Test-Ergebnis für ${testId}\n\n(Detaillierte Ansicht wird implementiert)`);
    }

    exportResults() {
        if (!this.currentTest) return;

        const dataStr = JSON.stringify(this.currentTest, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `stack-test-${this.currentTest.test_id}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    runAnotherTest() {
        this.resetUI();
    }

    cancelTest() {
        if (confirm('Möchten Sie den Test wirklich abbrechen?')) {
            clearInterval(this.testInterval);
            this.resetUI();
        }
    }

    resetUI() {
        document.getElementById('testSelectionCard').style.display = 'block';
        document.getElementById('runningTestCard').style.display = 'none';
        document.getElementById('resultsCard').style.display = 'none';
        this.currentTest = null;
    }
}

// Globale Instanz
let testingManager;

// Initialisierung
document.addEventListener('DOMContentLoaded', () => {
    testingManager = new TestingManager();
});
