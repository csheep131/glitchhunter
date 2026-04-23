/**
 * GlitchHunter Web-UI - History Manager
 * 
 * Verwaltet History-Ansicht:
 * - Analyse-History
 * - Problem-History
 * - Report-History
 * - Timeline mit Chart.js
 */

class HistoryManager {
    constructor() {
        this.apiBase = '/api/v1/history';
        this.chart = null;
        
        this.init();
    }

    /**
     * Initialisiert History-Manager
     */
    init() {
        console.log('[History] Initialisiere...');
        
        // Tab-Handler
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Button-Handler
        document.getElementById('refreshAnalysisBtn')?.addEventListener('click', () => this.loadAnalysisHistory());
        document.getElementById('refreshProblemsBtn')?.addEventListener('click', () => this.loadProblemHistory());
        document.getElementById('refreshReportsBtn')?.addEventListener('click', () => this.loadReportHistory());
        document.getElementById('cleanupOldBtn')?.addEventListener('click', () => this.cleanupOld());
        
        // Filter-Handler
        document.getElementById('analysisStatusFilter')?.addEventListener('change', () => this.loadAnalysisHistory());
        document.getElementById('analysisRepoFilter')?.addEventListener('input', () => this.loadAnalysisHistory());
        
        // Timeline-Days-Handler
        document.getElementById('timelineDays')?.addEventListener('change', (e) => this.loadTimeline(e.target.value));

        // Initiale Ladung
        this.loadStatistics();
        this.loadAnalysisHistory();
        this.loadTimeline(30);

        console.log('[History] Initialisierung abgeschlossen');
    }

    /**
     * Wechselt Tab
     */
    switchTab(tabId) {
        console.log('[History] Wechsle Tab:', tabId);
        
        // Tabs aktualisieren
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        // Content aktualisieren
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabId}-content`);
        });

        // Daten laden wenn nötig
        if (tabId === 'analysis') this.loadAnalysisHistory();
        else if (tabId === 'problems') this.loadProblemHistory();
        else if (tabId === 'reports') this.loadReportHistory();
        else if (tabId === 'timeline') this.loadTimeline(30);
    }

    /**
     * Lädt Statistiken
     */
    async loadStatistics() {
        try {
            const response = await fetch(`${this.apiBase}/statistics?days=30`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const stats = await response.json();
            console.log('[History] Statistiken geladen:', stats);

            // Stats anzeigen
            const analysis = stats.analysis || {};
            document.getElementById('statTotalAnalyses').textContent = analysis.total_analyses || 0;
            document.getElementById('statTotalFindings').textContent = analysis.total_findings || 0;
            document.getElementById('statAvgDuration').textContent = `${(analysis.avg_duration || 0).toFixed(1)}s`;
            
            const successRate = analysis.total_analyses > 0 
                ? ((analysis.completed || 0) / analysis.total_analyses * 100).toFixed(0)
                : 0;
            document.getElementById('statSuccessRate').textContent = `${successRate}%`;

        } catch (error) {
            console.error('[History] Fehler beim Laden der Statistiken:', error);
        }
    }

    /**
     * Lädt Analyse-History
     */
    async loadAnalysisHistory() {
        try {
            const status = document.getElementById('analysisStatusFilter').value;
            const repo = document.getElementById('analysisRepoFilter').value;
            
            const params = new URLSearchParams();
            if (status) params.append('status', status);
            if (repo) params.append('repo', repo);
            
            const response = await fetch(`${this.apiBase}/analysis?${params}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const history = await response.json();
            console.log('[History] Analyse-History geladen:', history.length);

            this.renderAnalysisList(history);

        } catch (error) {
            console.error('[History] Fehler beim Laden:', error);
            this.renderEmpty('analysisList', 'Fehler beim Laden der Analyse-History');
        }
    }

    /**
     * Rendert Analyse-Liste
     */
    renderAnalysisList(history) {
        const list = document.getElementById('analysisList');
        if (!list) return;

        if (!history || history.length === 0) {
            this.renderEmpty('analysisList', 'Keine Analysen gefunden');
            return;
        }

        list.innerHTML = history.map(item => `
            <div class="history-item ${item.status}">
                <div class="history-header">
                    <span class="history-title">📊 ${this.escapeHtml(item.repo_path)}</span>
                    <span class="history-status status-${item.status}">${item.status}</span>
                </div>
                <div class="history-meta">
                    <span class="meta-item">🆔 ${item.job_id}</span>
                    <span class="meta-item">📁 Stack: ${item.stack}</span>
                    <span class="meta-item">🔍 ${item.findings_count} Findings</span>
                    <span class="meta-item">⏱️ ${(item.duration_seconds || 0).toFixed(1)}s</span>
                    <span class="meta-item">🕐 ${new Date(item.created_at).toLocaleString('de-DE')}</span>
                </div>
                ${item.findings_count > 0 ? `
                    <div class="history-details">
                        🔴 ${item.critical_count || 0} Critical | 
                        🟠 ${item.high_count || 0} High | 
                        🟡 ${item.medium_count || 0} Medium | 
                        🟢 ${item.low_count || 0} Low
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    /**
     * Lädt Problem-History
     */
    async loadProblemHistory() {
        try {
            const response = await fetch(`${this.apiBase}/problems?limit=50`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const history = await response.json();
            console.log('[History] Problem-History geladen:', history.length);

            this.renderProblemList(history);

        } catch (error) {
            console.error('[History] Fehler beim Laden:', error);
            this.renderEmpty('problemsList', 'Fehler beim Laden der Problem-History');
        }
    }

    /**
     * Rendert Problem-Liste
     */
    renderProblemList(history) {
        const list = document.getElementById('problemsList');
        if (!list) return;

        if (!history || history.length === 0) {
            this.renderEmpty('problemsList', 'Keine Probleme gefunden');
            return;
        }

        list.innerHTML = history.map(item => `
            <div class="history-item ${item.status}">
                <div class="history-header">
                    <span class="history-title">🧠 ${this.escapeHtml(item.prompt.substring(0, 80))}${item.prompt.length > 80 ? '...' : ''}</span>
                    <span class="history-status status-${item.status}">${item.status}</span>
                </div>
                <div class="history-meta">
                    <span class="meta-item">🆔 ${item.problem_id}</span>
                    ${item.classification ? `<span class="meta-item">🏷️ ${item.classification}</span>` : ''}
                    <span class="meta-item">⏱️ ${(item.duration_seconds || 0).toFixed(1)}s</span>
                    <span class="meta-item">🕐 ${new Date(item.created_at).toLocaleString('de-DE')}</span>
                </div>
            </div>
        `).join('');
    }

    /**
     * Lädt Report-History
     */
    async loadReportHistory() {
        try {
            const response = await fetch(`${this.apiBase}/reports?limit=50`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const history = await response.json();
            console.log('[History] Report-History geladen:', history.length);

            this.renderReportList(history);

        } catch (error) {
            console.error('[History] Fehler beim Laden:', error);
            this.renderEmpty('reportsList', 'Fehler beim Laden der Report-History');
        }
    }

    /**
     * Rendert Report-Liste
     */
    renderReportList(history) {
        const list = document.getElementById('reportsList');
        if (!list) return;

        if (!history || history.length === 0) {
            this.renderEmpty('reportsList', 'Keine Reports gefunden');
            return;
        }

        list.innerHTML = history.map(item => `
            <div class="history-item ${item.format}">
                <div class="history-header">
                    <span class="history-title">📄 Report ${item.report_id}</span>
                    <span class="history-status format-${item.format}">${item.format}</span>
                </div>
                <div class="history-meta">
                    <span class="meta-item">🕐 ${new Date(item.created_at).toLocaleString('de-DE')}</span>
                    ${item.job_id ? `<span class="meta-item">📊 Job: ${item.job_id}</span>` : ''}
                    ${item.problem_id ? `<span class="meta-item">🧠 Problem: ${item.problem_id}</span>` : ''}
                </div>
            </div>
        `).join('');
    }

    /**
     * Lädt Timeline-Daten
     */
    async loadTimeline(days) {
        try {
            const response = await fetch(`${this.apiBase}/daily-stats?days=${days}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const stats = await response.json();
            console.log('[History] Timeline-Daten geladen:', stats.length);

            this.renderChart(stats);
            this.renderTimelineList(stats);

        } catch (error) {
            console.error('[History] Fehler beim Laden der Timeline:', error);
        }
    }

    /**
     * Rendert Chart.js Diagramm
     */
    renderChart(stats) {
        const ctx = document.getElementById('dailyStatsChart');
        if (!ctx) return;

        // Daten vorbereiten
        const labels = stats.map(s => s.date).reverse();
        const data = stats.map(s => s.total_analyses).reverse();

        // Alten Chart zerstören wenn vorhanden
        if (this.chart) {
            this.chart.destroy();
        }

        // Neuen Chart erstellen
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Analysen pro Tag',
                    data: data,
                    backgroundColor: 'rgba(212, 196, 168, 0.6)',
                    borderColor: 'rgba(212, 196, 168, 1)',
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.parsed.y} Analysen`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    /**
     * Rendert Timeline-Liste
     */
    renderTimelineList(stats) {
        const list = document.getElementById('timelineList');
        if (!list) return;

        if (!stats || stats.length === 0) {
            list.innerHTML = '<div class="empty-state"><p>Keine Daten verfügbar</p></div>';
            return;
        }

        list.innerHTML = stats.map(day => `
            <div class="timeline-day">
                <div class="timeline-day-header">
                    <span class="timeline-day-title">${new Date(day.date).toLocaleDateString('de-DE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
                    <div class="timeline-day-stats">
                        <span>📊 ${day.total_analyses} Analysen</span>
                        <span>🔍 ${day.total_findings || 0} Findings</span>
                        <span>⏱️ ${(day.avg_duration || 0).toFixed(1)}s Ø</span>
                        <span>✅ ${day.completed_count} erfolgreich</span>
                        ${day.failed_count > 0 ? `<span>❌ ${day.failed_count} fehlgeschlagen</span>` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Rendert Empty State
     */
    renderEmpty(elementId, message) {
        const list = document.getElementById(elementId);
        if (!list) return;

        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📜</div>
                <div class="empty-state-text">${message}</div>
            </div>
        `;
    }

    /**
     * Bereinigt alte Einträge
     */
    async cleanupOld() {
        const days = prompt('Einträge älter als wie viele Tage löschen?', '90');
        if (!days) return;

        try {
            const response = await fetch(`${this.apiBase}/cleanup?older_than_days=${parseInt(days)}`, {
                method: 'POST',
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            alert(`✅ Einträge älter als ${days} Tage gelöscht`);
            this.loadStatistics();
            this.loadAnalysisHistory();

        } catch (error) {
            console.error('[History] Fehler beim Bereinigen:', error);
            alert(`Fehler: ${error.message}`);
        }
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Globale Instanz
let historyManager;

// Initialisierung wenn DOM geladen ist
document.addEventListener('DOMContentLoaded', () => {
    historyManager = new HistoryManager();
});
