/**
 * GlitchHunter Web-UI - Problem Solver
 * 
 * Verwaltet prompt-basierte Problemlösung:
 * - Prompt-Eingabe
 * - WebSocket für Live-Updates
 * - Status-Timeline
 * - Ergebnis-Anzeige
 */

class ProblemSolver {
    constructor() {
        this.currentProblemId = null;
        this.websocket = null;
        this.apiBase = '/api/v1/problem';
        
        this.init();
    }

    /**
     * Initialisiert Problem-Solver
     */
    init() {
        console.log('[Problem] Initialisiere...');
        
        // Form-Handler
        document.getElementById('promptForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.solveProblem();
        });

        // Button-Handler
        document.getElementById('applySolutionBtn')?.addEventListener('click', () => this.applySolution());
        document.getElementById('newProblemBtn')?.addEventListener('click', () => this.reset());

        console.log('[Problem] Initialisierung abgeschlossen');
    }

    /**
     * Startet Problemlösung
     */
    async solveProblem() {
        const prompt = document.getElementById('promptInput').value;
        const repoPath = document.getElementById('repoPath').value;
        const withMl = document.getElementById('withMlPrediction').checked;
        const withAnalysis = document.getElementById('withCodeAnalysis').checked;
        const autoFix = document.getElementById('autoFix').checked;
        const stack = document.getElementById('stackSelect').value;

        console.log('[Problem] Starte Problemlösung:', prompt.substring(0, 50) + '...');

        // UI aktualisieren
        this.showStatusCard();
        this.updateStep('intake', 'active');
        this.updateStatus('Starte Analyse...', 'running');
        this.addLog('Info', 'Sende Problem an Server...');

        const btn = document.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.textContent = '⏳ Analysiere...';

        try {
            const response = await fetch(`${this.apiBase}/solve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: prompt,
                    repo_path: repoPath || undefined,
                    with_ml_prediction: withMl,
                    with_code_analysis: withAnalysis,
                    auto_fix: autoFix,
                    stack: stack,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('[Problem] Problem gestartet, ID:', data.problem_id);

            this.currentProblemId = data.problem_id;
            this.addLog('Success', `Problem-ID: ${data.problem_id}`);

            // WebSocket verbinden
            this.connectWebSocket(data.problem_id);

        } catch (error) {
            console.error('[Problem] Fehler beim Starten:', error);
            this.addLog('Error', `Fehler: ${error.message}`);
            this.updateStatus('Fehler aufgetreten', 'error');
            btn.disabled = false;
            btn.textContent = '🚀 Problem analysieren';
        }
    }

    /**
     * Verbindet WebSocket für Live-Updates
     */
    connectWebSocket(problemId) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${this.apiBase}/ws/${problemId}`;

        console.log('[WebSocket] Verbinde mit:', wsUrl);
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('[WebSocket] Verbunden');
            this.addLog('Info', 'WebSocket verbunden');
        };

        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('[WebSocket] Nachricht:', data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('[WebSocket] Parse-Fehler:', error);
            }
        };

        this.websocket.onerror = (error) => {
            console.error('[WebSocket] Fehler:', error);
            this.addLog('Error', 'WebSocket-Fehler');
        };

        this.websocket.onclose = () => {
            console.log('[WebSocket] Getrennt');
            this.addLog('Info', 'WebSocket getrennt');
        };

        // Keep-Alive
        setInterval(() => {
            if (this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send('ping');
            }
        }, 30000);
    }

    /**
     * Verarbeitet WebSocket-Nachrichten
     */
    handleWebSocketMessage(data) {
        const { type, problem_id, status, message, classification, diagnosis, plan, solution, error } = data;

        switch (type) {
            case 'intake_complete':
                this.updateStep('intake', 'completed');
                this.updateStep('classify', 'active');
                this.updateStatus(message || 'Problem erfasst...', 'running');
                this.addLog('Info', message);
                break;

            case 'classifying':
                this.updateStatus(message || 'Klassifiziere...', 'running');
                this.addLog('Info', message);
                break;

            case 'classified':
                this.updateStep('classify', 'completed');
                this.updateStep('diagnose', 'active');
                this.updateStatus(message || 'Klassifikation abgeschlossen', 'running');
                this.addLog('Success', `Klassifikation: ${classification}`);
                this.displayClassification(classification);
                break;

            case 'diagnosing':
                this.updateStatus(message || 'Diagnose läuft...', 'running');
                this.addLog('Info', message);
                break;

            case 'diagnosed':
                this.updateStep('diagnose', 'completed');
                this.updateStep('plan', 'active');
                this.updateStatus(message || 'Diagnose abgeschlossen', 'running');
                this.addLog('Success', 'Diagnose erstellt');
                this.displayDiagnosis(diagnosis);
                break;

            case 'planning':
                this.updateStatus(message || 'Erstelle Plan...', 'running');
                this.addLog('Info', message);
                break;

            case 'planned':
                this.updateStep('plan', 'completed');
                this.updateStep('fix', 'active');
                this.updateStatus(message || 'Plan erstellt', 'running');
                this.addLog('Success', 'Lösungsplan erstellt');
                this.displayPlan(plan);
                break;

            case 'fixing':
                this.updateStatus(message || 'Wende Fix an...', 'running');
                this.addLog('Info', message);
                break;

            case 'completed':
                this.updateStep('fix', 'completed');
                this.updateStatus(message || 'Problem gelöst!', 'completed');
                this.addLog('Success', message);
                this.displaySolution(solution);
                this.showResultCard();
                
                // Button re-enable
                const btn = document.querySelector('button[type="submit"]');
                btn.disabled = false;
                btn.textContent = '🔄 Neu starten';
                break;

            case 'error':
                this.updateStatus(error || 'Fehler aufgetreten', 'error');
                this.addLog('Error', error);
                
                const btn = document.querySelector('button[type="submit"]');
                btn.disabled = false;
                btn.textContent = '❌ Fehler - Erneut versuchen';
                break;

            default:
                console.log('[WebSocket] Unbekannter Typ:', type);
        }
    }

    /**
     * Aktualisiert Timeline-Step
     */
    updateStep(stepId, status) {
        const step = document.getElementById(`step-${stepId}`);
        if (!step) return;

        step.classList.remove('active', 'completed');
        if (status) {
            step.classList.add(status);
        }

        const statusEl = step.querySelector('.step-status');
        if (statusEl) {
            switch (status) {
                case 'active':
                    statusEl.textContent = 'Läuft...';
                    break;
                case 'completed':
                    statusEl.textContent = 'Abgeschlossen';
                    break;
                default:
                    statusEl.textContent = 'Ausstehend';
            }
        }
    }

    /**
     * Aktualisiert Status-Anzeige
     */
    updateStatus(text, type) {
        const statusEl = document.getElementById('statusText');
        const indicatorEl = document.querySelector('.status-indicator');

        if (statusEl) {
            statusEl.textContent = text;
        }

        if (indicatorEl) {
            indicatorEl.className = 'status-indicator';
            if (type) {
                indicatorEl.classList.add(type);
            }
        }
    }

    /**
     * Fügt Log-Eintrag hinzu
     */
    addLog(type, message) {
        const logEl = document.getElementById('progressLog');
        if (!logEl) return;

        const now = new Date().toLocaleTimeString();
        const logClass = `log-${type.toLowerCase()}`;
        
        const entry = document.createElement('div');
        entry.className = `log-entry ${logClass}`;
        entry.innerHTML = `<span class="log-time">[${now}]</span> ${message}`;
        
        logEl.appendChild(entry);
        logEl.scrollTop = logEl.scrollHeight;
    }

    /**
     * Zeigt Status-Card
     */
    showStatusCard() {
        document.getElementById('statusCard').style.display = 'block';
        document.getElementById('promptCard').style.opacity = '0.5';
        document.getElementById('promptCard').style.pointerEvents = 'none';
    }

    /**
     * Zeigt Ergebnis-Card
     */
    showResultCard() {
        document.getElementById('resultCard').style.display = 'block';
        document.getElementById('resultCard').scrollIntoView({ behavior: 'smooth' });
    }

    /**
     * Zeigt Klassifikation
     */
    displayClassification(classification) {
        const el = document.getElementById('resultClassification');
        if (el) {
            el.innerHTML = classification ? this.formatText(classification) : '-';
        }
    }

    /**
     * Zeigt Diagnose
     */
    displayDiagnosis(diagnosis) {
        const el = document.getElementById('resultDiagnosis');
        if (el) {
            el.innerHTML = diagnosis ? this.formatText(diagnosis) : '-';
        }
    }

    /**
     * Zeigt Plan
     */
    displayPlan(plan) {
        const el = document.getElementById('resultPlan');
        if (el) {
            el.innerHTML = plan ? this.formatText(plan) : '-';
        }
    }

    /**
     * Zeigt Lösung
     */
    displaySolution(solution) {
        const el = document.getElementById('resultSolution');
        if (el) {
            el.innerHTML = solution ? this.formatText(solution) : '-';
        }
    }

    /**
     * Formatiert Text (Code-Blöcke erkennen)
     */
    formatText(text) {
        if (!text) return '-';
        
        // Code-Blöcke erkennen und formatieren
        return text
            .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    /**
     * Wendet Lösung an
     */
    async applySolution() {
        if (!this.currentProblemId) return;

        const btn = document.getElementById('applySolutionBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Wende an...';

        try {
            // TODO: Echte Implementierung mit Code-Changes
            console.log('[Problem] Wende Lösung an...');
            
            alert('Lösung wurde angewendet (Demo)');
            
        } catch (error) {
            console.error('[Problem] Fehler beim Anwenden:', error);
            alert(`Fehler: ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = '💡 Lösung anwenden';
        }
    }

    /**
     * Setzt UI zurück
     */
    reset() {
        this.currentProblemId = null;
        this.currentProblem = null;

        // Cards ausblenden
        document.getElementById('statusCard').style.display = 'none';
        document.getElementById('resultCard').style.display = 'none';
        document.getElementById('promptCard').style.opacity = '1';
        document.getElementById('promptCard').style.pointerEvents = 'auto';

        // Form zurücksetzen
        document.getElementById('promptForm').reset();

        // Timeline zurücksetzen
        ['intake', 'classify', 'diagnose', 'plan', 'fix'].forEach(step => {
            this.updateStep(step, '');
        });

        // Logs leeren
        document.getElementById('progressLog').innerHTML = '';

        // Button zurücksetzen
        const btn = document.querySelector('button[type="submit"]');
        btn.disabled = false;
        btn.textContent = '🚀 Problem analysieren';

        console.log('[Problem] Zurückgesetzt');
    }
}

// Globale Instanz
let problemSolver;

// Initialisierung wenn DOM geladen ist
document.addEventListener('DOMContentLoaded', () => {
    problemSolver = new ProblemSolver();
});
