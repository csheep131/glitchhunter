/**
 * GlitchHunter Web-UI - Reports Manager
 * 
 * Verwaltet Report-Generierung:
 * - Reports erstellen
 * - Übersicht anzeigen
 * - Vorschau und Download
 */

class ReportsManager {
    constructor() {
        this.currentReport = null;
        this.apiBase = '/api/v1/reports';
        
        this.init();
    }

    /**
     * Initialisiert Reports-Manager
     */
    init() {
        console.log('[Reports] Initialisiere...');
        
        // Form-Handler
        document.getElementById('newReportForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateReport();
        });

        // Button-Handler
        document.getElementById('refreshBtn')?.addEventListener('click', () => this.loadReports());
        document.getElementById('deleteAllBtn')?.addEventListener('click', () => this.deleteAll());
        document.getElementById('downloadBtn')?.addEventListener('click', () => this.downloadCurrentReport());
        document.getElementById('deleteBtn')?.addEventListener('click', () => this.deleteCurrentReport());

        // Reports laden
        this.loadReports();

        console.log('[Reports] Initialisierung abgeschlossen');
    }

    /**
     * Generiert neuen Report
     */
    async generateReport() {
        const jobId = document.getElementById('jobIdInput').value;
        const problemId = document.getElementById('problemIdInput').value;
        const format = document.getElementById('formatSelect').value;
        const includeRaw = document.getElementById('includeRawData').checked;

        console.log('[Reports] Generiere Report:', { jobId, problemId, format, includeRaw });

        const btn = document.querySelector('#newReportForm button[type="submit"]');
        btn.disabled = true;
        btn.textContent = '⏳ Generiere...';

        try {
            const response = await fetch(`${this.apiBase}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: jobId || undefined,
                    problem_id: problemId || undefined,
                    format: format,
                    include_raw_data: includeRaw,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('[Reports] Report generiert:', data);

            alert(`✅ Report generiert!\n\nID: ${data.report_id}\nFormat: ${data.format}\n\nDownload: ${data.download_url}`);

            // Form zurücksetzen
            document.getElementById('newReportForm').reset();

            // Reports neu laden
            this.loadReports();

        } catch (error) {
            console.error('[Reports] Fehler beim Generieren:', error);
            alert(`❌ Fehler beim Generieren: ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = '📊 Report generieren';
        }
    }

    /**
     * Lädt alle Reports
     */
    async loadReports() {
        try {
            console.log('[Reports] Lade Reports...');

            const response = await fetch(this.apiBase);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reports = await response.json();
            console.log('[Reports] Geladene Reports:', reports.length);

            this.renderReports(reports);

        } catch (error) {
            console.error('[Reports] Fehler beim Laden:', error);
            this.renderEmpty('Fehler beim Laden der Reports');
        }
    }

    /**
     * Rendert Reports-Liste
     */
    renderReports(reports) {
        const list = document.getElementById('reportsList');
        const card = document.getElementById('reportsListCard');
        
        if (!list || !card) return;

        if (!reports || reports.length === 0) {
            this.renderEmpty('Keine Reports vorhanden');
            return;
        }

        card.style.display = 'block';
        list.innerHTML = reports.map(report => `
            <div class="report-item ${report.format}" onclick="reportsManager.showPreview('${report.report_id}')">
                <div class="report-header">
                    <span class="report-title">${this.escapeHtml(report.title)}</span>
                    <span class="report-format format-${report.format}">${report.format}</span>
                </div>
                <div class="report-meta">
                    <span class="meta-item">🕐 ${new Date(report.generated_at).toLocaleString('de-DE')}</span>
                    <span class="meta-item">📁 ${report.report_id}</span>
                    ${report.metadata?.job_id ? `<span class="meta-item">📊 Job: ${report.metadata.job_id}</span>` : ''}
                    ${report.metadata?.problem_id ? `<span class="meta-item">🧠 Problem: ${report.metadata.problem_id}</span>` : ''}
                </div>
            </div>
        `).join('');
    }

    /**
     * Rendert Empty State
     */
    renderEmpty(message) {
        const list = document.getElementById('reportsList');
        const card = document.getElementById('reportsListCard');
        
        if (!list || !card) return;

        card.style.display = 'block';
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📊</div>
                <div class="empty-state-text">${message}</div>
                <div class="empty-state-hint">Erstellen Sie einen neuen Report um zu beginnen</div>
            </div>
        `;
    }

    /**
     * Zeigt Report-Vorschau
     */
    async showPreview(reportId) {
        try {
            console.log('[Reports] Zeige Vorschau:', reportId);

            const response = await fetch(`${this.apiBase}/${reportId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            this.currentReport = await response.json();
            console.log('[Reports] Report geladen:', this.currentReport);

            // Modal füllen
            document.getElementById('previewTitle').textContent = this.currentReport.title;
            document.getElementById('previewFormat').textContent = this.currentReport.format.toUpperCase();
            document.getElementById('previewDate').textContent = new Date(this.currentReport.generated_at).toLocaleString('de-DE');
            document.getElementById('previewId').textContent = this.currentReport.report_id;

            // Inhalt anzeigen
            const contentEl = document.getElementById('previewContent');
            contentEl.textContent = this.currentReport.content;
            contentEl.className = `preview-content ${this.currentReport.format}`;

            // Modal anzeigen
            document.getElementById('previewModal').style.display = 'flex';

        } catch (error) {
            console.error('[Reports] Fehler beim Laden:', error);
            alert(`Fehler beim Laden: ${error.message}`);
        }
    }

    /**
     * Lädt aktuellen Report herunter
     */
    downloadCurrentReport() {
        if (!this.currentReport) return;

        const downloadUrl = `${this.apiBase}/${this.currentReport.report_id}/download`;
        window.open(downloadUrl, '_blank');
    }

    /**
     * Löscht aktuellen Report
     */
    async deleteCurrentReport() {
        if (!this.currentReport) return;

        if (!confirm(`Möchten Sie den Report "${this.currentReport.title}" wirklich löschen?`)) {
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/${this.currentReport.report_id}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            console.log('[Reports] Report gelöscht');
            closePreview();
            this.loadReports();

        } catch (error) {
            console.error('[Reports] Fehler beim Löschen:', error);
            alert(`Fehler beim Löschen: ${error.message}`);
        }
    }

    /**
     * Löscht alle Reports
     */
    async deleteAll() {
        if (!confirm('Möchten Sie wirklich ALLE Reports löschen?')) {
            return;
        }

        try {
            const reports = await (await fetch(this.apiBase)).json();
            
            for (const report of reports) {
                await fetch(`${this.apiBase}/${report.report_id}`, {
                    method: 'DELETE',
                });
            }

            console.log('[Reports] Alle Reports gelöscht');
            this.loadReports();

        } catch (error) {
            console.error('[Reports] Fehler beim Löschen:', error);
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
let reportsManager;

// Modal-Funktionen
function closePreview() {
    document.getElementById('previewModal').style.display = 'none';
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
    reportsManager = new ReportsManager();
});
