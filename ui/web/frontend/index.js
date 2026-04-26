/**
 * GlitchHunter v3.0 - Dashboard Manager
 * Live data, auto-refresh, WebSocket updates
 */

class DashboardManager {
    constructor() {
        this.apiBase = '/api/v1';
        this.ws = null;
        this.refreshInterval = null;
        this.refreshRate = 5000; // 5 seconds
        this.currentJobId = null;
        this.jobs = [];
        this.systemStatus = null;

        this.init();
    }

    async init() {
        console.log('[Dashboard] Initialisiere...');

        // Event Listeners
        document.getElementById('analyzeBtn')?.addEventListener('click', () => this.startAnalysis());
        document.getElementById('browseBtn')?.addEventListener('click', () => this.openFolderBrowser());

        // Initial load
        await Promise.all([
            this.loadStats(),
            this.loadJobs(),
            this.loadSystemHealth(),
            this.loadStacks(),
            this.loadProjectList(),
            this.loadLlamaStatus(),
            this.sshfsCheckStatus(),
        ]);

        // Auto-refresh
        this.refreshInterval = setInterval(() => {
            this.loadStats();
            this.loadJobs();
            this.loadSystemHealth();
            this.loadLlamaStatus();
        }, this.refreshRate);

        console.log('[Dashboard] Initialisiert, Auto-Refresh alle', this.refreshRate, 'ms');
    }

    // ─── Stats ──────────────────────────────────────────────────────────

    async loadStats() {
        try {
            const [statusRes, jobsRes] = await Promise.all([
                fetch(`${this.apiBase}/status`),
                fetch(`${this.apiBase}/jobs`),
            ]);

            const status = await statusRes.json();
            const jobs = await jobsRes.json();

            // Gesamt-Jobs
            document.getElementById('stat-jobs').textContent = jobs.length || '0';

            // Findings aus completed Jobs
            let totalFindings = 0;
            let totalCritical = 0;
            let totalDuration = 0;
            let completedCount = 0;

            for (const job of jobs) {
                if (job.status === 'completed' && job.findings) {
                    totalFindings += job.findings.length;
                    totalCritical += job.findings.filter(f => f.severity === 'critical').length;
                    completedCount++;
                }
                if (job.execution_time) {
                    totalDuration += job.execution_time;
                }
            }

            document.getElementById('stat-findings').textContent = totalFindings;
            document.getElementById('stat-critical').textContent = totalCritical;

            const avgTime = completedCount > 0 ? (totalDuration / completedCount).toFixed(0) : '—';
            document.getElementById('stat-time').textContent = avgTime !== '—' ? `${avgTime}s` : '—';

            this.systemStatus = status;
        } catch (error) {
            console.error('[Dashboard] Fehler beim Laden der Stats:', error);
        }
    }

    // ─── Jobs ───────────────────────────────────────────────────────────

    async loadJobs() {
        try {
            const res = await fetch(`${this.apiBase}/jobs`);
            this.jobs = await res.json();

            this.renderActiveJobs();
            this.renderRecentJobs();
        } catch (error) {
            console.error('[Dashboard] Fehler beim Laden der Jobs:', error);
        }
    }

    renderActiveJobs() {
        const activeJobs = this.jobs.filter(j => j.status === 'running' || j.status === 'pending');
        const listEl = document.getElementById('activeJobsList');
        const countEl = document.getElementById('activeCount');

        countEl.textContent = activeJobs.length;

        if (activeJobs.length === 0) {
            listEl.innerHTML = '<p class="text-muted text-center py-6">Keine aktiven Jobs</p>';
            return;
        }

        listEl.innerHTML = activeJobs.map(job => `
            <div class="active-job-item fade-in" onclick="dashboard.showJobDetail('${job.id}')">
                <div class="active-job-header">
                    <span class="active-job-repo">${this.escapeHtml(job.repo_path || 'unknown')}</span>
                    <span class="active-job-stack">${job.stack || 'stack_b'}</span>
                </div>
                <div class="active-job-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${job.status === 'running' ? '50' : '10'}%"></div>
                    </div>
                </div>
                <div class="active-job-meta">
                    <span>⏱️ <span class="job-duration" data-started="${job.started_at}">—</span></span>
                    <span>📊 ${job.status}</span>
                </div>
            </div>
        `).join('');

        // Berechne Dauer
        this.updateDurations();
    }

    renderRecentJobs() {
        const tbody = document.getElementById('recentJobsBody');
        const recentJobs = this.jobs.slice(0, 10);

        if (recentJobs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-center py-6">Keine Jobs vorhanden</td></tr>';
            return;
        }

        tbody.innerHTML = recentJobs.map(job => {
            const findingsCount = job.findings ? job.findings.length : 0;
            const criticalCount = job.findings ? job.findings.filter(f => f.severity === 'critical').length : 0;
            const duration = job.execution_time ? `${job.execution_time.toFixed(1)}s` : '—';
            const started = job.started_at ? new Date(job.started_at).toLocaleTimeString('de-DE') : '—';

            return `
                <tr onclick="dashboard.showJobDetail('${job.id}')">
                    <td><span class="job-status ${job.status}">${job.status}</span></td>
                    <td class="repo-cell" title="${this.escapeHtml(job.repo_path || '')}">${this.escapeHtml(this.shortenPath(job.repo_path || ''))}</td>
                    <td>${job.stack || '—'}</td>
                    <td>${findingsCount}${criticalCount > 0 ? ` <span style="color: var(--color-red)">(${criticalCount} kritisch)</span>` : ''}</td>
                    <td>${duration}</td>
                    <td>${started}</td>
                    <td>
                        <div class="job-actions">
                            ${findingsCount > 0 ? `<button class="job-action-btn" onclick="event.stopPropagation(); dashboard.exportJob('${job.id}', 'json')">JSON</button>` : ''}
                            ${findingsCount > 0 ? `<button class="job-action-btn" onclick="event.stopPropagation(); dashboard.exportJob('${job.id}', 'md')">MD</button>` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // ─── System Health ──────────────────────────────────────────────────

    async loadSystemHealth() {
        try {
            const res = await fetch(`${this.apiBase}/status`);
            const status = await res.json();

            const healthEl = document.getElementById('systemHealth');
            const badgeEl = document.getElementById('systemStatusBadge');

            const isHealthy = status.status === 'healthy';
            badgeEl.textContent = isHealthy ? 'Healthy' : 'Warning';
            badgeEl.className = `badge ${isHealthy ? 'badge-success' : 'badge-warning'}`;

            healthEl.innerHTML = `
                <div class="health-item">
                    <div class="health-indicator ${isHealthy ? 'online' : 'error'}"></div>
                    <span class="health-name">API Server</span>
                    <span class="health-detail">v${status.version || '?'}</span>
                </div>
                <div class="health-item">
                    <div class="health-indicator ${status.active_jobs === 0 ? 'online' : 'warning'}"></div>
                    <span class="health-name">Aktive Jobs</span>
                    <span class="health-detail">${status.active_jobs} läuft / ${status.total_jobs} gesamt</span>
                </div>
            `;
        } catch (error) {
            console.error('[Dashboard] Fehler beim Laden des System-Health:', error);
        }
    }

    async loadStacks() {
        try {
            const res = await fetch(`${this.apiBase}/stacks`);
            const stacks = await res.json();

            const healthEl = document.getElementById('systemHealth');
            if (!healthEl) return;

            const stackItems = stacks.map(s => `
                <div class="health-item">
                    <div class="health-indicator ${s.enabled ? 'online' : 'offline'}"></div>
                    <span class="health-name">${s.name}</span>
                    <span class="health-detail">${s.hardware}</span>
                </div>
            `).join('');

            // Füge Stack-Items an healthEl an
            healthEl.insertAdjacentHTML('beforeend', stackItems);
        } catch (error) {
            console.error('[Dashboard] Fehler beim Laden der Stacks:', error);
        }
    }

    // ─── Project Discovery ──────────────────────────────────────────

    async loadProjectList() {
        try {
            const res = await fetch('/api/v1/discover/projects');
            const data = await res.json();
            const datalist = document.getElementById('dashboardProjectList');
            if (!datalist) return;
            
            let options = [];
            
            // Lokale Projekte
            if (data.projects && data.projects.length > 0) {
                options = data.projects.map(p =>
                    `<option value="${p}">📁 ${p.replace('/home/schaf/projects/', '')}</option>`
                );
            }
            
            // Remote-Projekte (SSHFS)
            if (data.remote_projects && data.remote_projects.length > 0) {
                options.push(`<option disabled>────────── Remote (SSHFS) ──────────</option>`);
                options = options.concat(data.remote_projects.map(p =>
                    `<option value="${p}">🔗 ${p.replace('/mnt/remote/', '')}</option>`
                ));
            }
            
            datalist.innerHTML = options.join('');
            console.log(`[Dashboard] ${data.count} lokal + ${data.remote_count} remote Projekte geladen`);
        } catch (error) {
            console.error('[Dashboard] Fehler beim Laden der Projektliste:', error);
        }
    }
    
    async loadLlamaStatus() {
        try {
            const res = await fetch('/api/v1/models/llama_status');
            const status = await res.json();
            
            const container = document.getElementById('llamaStatusWidget');
            if (!container) return;
            
            const running = status.llama_running;
            const vramPct = status.vram_usage_pct || 0;
            const vramUsed = (status.vram_used_mb / 1024).toFixed(1);
            const vramTotal = (status.vram_total_mb / 1024).toFixed(1);
            const gpuName = status.gpu_name || 'N/A';
            const loadedModel = status.loaded_model;
            
            // VRAM-Farbe basierend auf Auslastung
            let vramColor = 'var(--color-green)';
            if (vramPct > 80) vramColor = 'var(--color-red)';
            else if (vramPct > 50) vramColor = 'var(--color-yellow)';
            
            container.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                    <div class="health-indicator ${running ? 'online' : 'offline'}"></div>
                    <span style="font-weight:600;">🦙 LLaMA.cpp</span>
                    <span class="badge ${running ? 'badge-success' : 'badge-warning'}">${running ? 'Läuft' : 'Gestoppt'}</span>
                    ${loadedModel ? `<span style="font-size:0.8em; color:var(--text-secondary); margin-left:auto;" title="${loadedModel}">📦 ${loadedModel.length > 25 ? loadedModel.slice(0,25)+'…' : loadedModel}</span>` : ''}
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:0.85em; min-width:50px;">🎮 ${gpuName.length > 20 ? gpuName.slice(0,20)+'…' : gpuName}</span>
                    <div style="flex:1; height:8px; background:var(--bg-tertiary); border-radius:4px; overflow:hidden;">
                        <div style="width:${vramPct}%; height:100%; background:${vramColor}; border-radius:4px; transition:width 0.5s;"></div>
                    </div>
                    <span style="font-size:0.8em; color:var(--text-secondary); min-width:80px; text-align:right;">${vramUsed}/${vramTotal} GB</span>
                </div>
            `;
        } catch (error) {
            const container = document.getElementById('llamaStatusWidget');
            if (container) {
                container.innerHTML = '<span style="color:var(--text-secondary); font-size:0.85em;">⚠️ LLaMA-Status nicht verfügbar</span>';
            }
        }
    }

    // ─── SSHFS Remote Mount ───────────────────────────────────────────

    async sshfsCheckStatus() {
        try {
            const res = await fetch('/api/v1/sshfs/status');
            const data = await res.json();
            
            const badge = document.getElementById('sshfsStatusBadge');
            const info = document.getElementById('sshfsInfo');
            const mountBtn = document.getElementById('sshfsMountBtn');
            const unmountBtn = document.getElementById('sshfsUnmountBtn');
            const projectsDiv = document.getElementById('sshfsProjects');
            
            if (data.mounted) {
                badge.textContent = 'Verbunden';
                badge.className = 'badge badge-success';
                info.textContent = `${data.host}:${data.remote_path} → ${data.mount_point}`;
                mountBtn.style.display = 'none';
                unmountBtn.style.display = 'inline-flex';
                
                // Remote-Projekte laden
                const projRes = await fetch('/api/v1/discover/projects/remote');
                const projData = await projRes.json();
                if (projData.projects && projData.projects.length > 0) {
                    projectsDiv.style.display = 'block';
                    document.getElementById('sshfsProjectList').innerHTML = projData.projects.slice(0, 20).map(p => 
                        `<button class="btn btn-ghost btn-sm" onclick="document.getElementById('repoPath').value='${p.path}'; dashboard.closeFolderBrowser();" title="${p.path}">🔗 ${p.name}</button>`
                    ).join('') + (projData.count > 20 ? `<span class="text-muted" style="font-size:0.8em;">+${projData.count - 20} weitere</span>` : '');
                }
            } else {
                badge.textContent = 'Getrennt';
                badge.className = 'badge badge-warning';
                info.textContent = data.configured ? `Nicht verbunden (${data.user}@${data.host})` : 'Nicht konfiguriert';
                mountBtn.style.display = data.configured ? 'inline-flex' : 'none';
                unmountBtn.style.display = 'none';
                projectsDiv.style.display = 'none';
            }
        } catch (error) {
            const badge = document.getElementById('sshfsStatusBadge');
            if (badge) { badge.textContent = 'Fehler'; badge.className = 'badge badge-error'; }
        }
    }
    
    async sshfsMount() {
        const btn = document.getElementById('sshfsMountBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Verbinde...';
        try {
            const res = await fetch('/api/v1/sshfs/mount', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                await this.sshfsCheckStatus();
                await this.loadProjectList();
            } else {
                alert('Mount fehlgeschlagen: ' + (data.error || data.message));
            }
        } catch (error) {
            alert('Fehler: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = '🔗 Verbinden';
        }
    }
    
    async sshfsUnmount() {
        const btn = document.getElementById('sshfsUnmountBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Trenne...';
        try {
            const res = await fetch('/api/v1/sshfs/unmount', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                await this.sshfsCheckStatus();
                await this.loadProjectList();
            } else {
                alert('Unmount fehlgeschlagen: ' + (data.error || data.message));
            }
        } catch (error) {
            alert('Fehler: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = '⏏️ Trennen';
        }
    }

    // ─── Analysis ───────────────────────────────────────────────────────

    async startAnalysis() {
        const repoPath = document.getElementById('repoPath').value.trim();
        if (!repoPath) {
            alert('Bitte Repository-Pfad eingeben');
            return;
        }

        const stack = document.getElementById('stackSelect').value;
        const useParallel = document.getElementById('useParallel').checked;
        const enableMl = document.getElementById('enableMl').checked;

        const btn = document.getElementById('analyzeBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Starte...';

        try {
            const response = await fetch(`${this.apiBase}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    repo_path: repoPath,
                    use_parallel: useParallel,
                    enable_ml_prediction: enableMl,
                    enable_auto_refactor: false,
                    max_workers: 4,
                    stack: stack,
                }),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();
            this.currentJobId = data.job_id;

            console.log('[Dashboard] Analyse gestartet:', data.job_id);

            // Felder beibehalten (NICHT zurücksetzen!)
            // WebSocket verbinden
            this.connectWebSocket(data.job_id);

            // Sofort Jobs refreshen
            await this.loadJobs();

        } catch (error) {
            console.error('[Dashboard] Fehler beim Starten:', error);
            alert('Fehler: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = '🚀 Starten';
        }
    }

    connectWebSocket(jobId) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/results/${jobId}`;

        console.log('[Dashboard] WebSocket:', wsUrl);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('[Dashboard] WebSocket verbunden');
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'status') {
                    this.loadJobs();
                } else if (data.type === 'complete') {
                    console.log('[Dashboard] Analyse abgeschlossen!');
                    this.loadJobs();
                    this.loadStats();
                    if (this.ws) this.ws.close();
                } else if (data.type === 'error') {
                    console.error('[Dashboard] Analyse-Fehler:', data.message);
                    this.loadJobs();
                    if (this.ws) this.ws.close();
                }
            } catch (e) {
                console.error('[Dashboard] WebSocket Parse Error:', e);
            }
        };

        this.ws.onerror = (error) => {
            console.error('[Dashboard] WebSocket Error:', error);
        };

        this.ws.onclose = () => {
            console.log('[Dashboard] WebSocket geschlossen');
            this.ws = null;
        };
    }

    // ─── Job Detail ─────────────────────────────────────────────────────

    async showJobDetail(jobId) {
        try {
            const res = await fetch(`${this.apiBase}/jobs/${jobId}`);
            const job = await res.json();

            document.getElementById('activeJobDetail').style.display = 'block';
            document.getElementById('detailRepo').textContent = job.repo_path || '—';
            document.getElementById('detailStatus').textContent = job.status;
            document.getElementById('detailStarted').textContent = job.started_at
                ? new Date(job.started_at).toLocaleString('de-DE')
                : '—';

            const progress = job.status === 'completed' ? 100 : job.status === 'running' ? 50 : job.status === 'failed' ? 100 : 10;
            document.getElementById('detailProgress').style.width = `${progress}%`;

            // Findings anzeigen
            const findingsEl = document.getElementById('detailFindings');
            if (job.findings && job.findings.length > 0) {
                findingsEl.innerHTML = `
                    <h3 style="margin-bottom: var(--spacing-3);">Findings (${job.findings.length})</h3>
                    <div class="findings-list">
                        ${job.findings.map(f => `
                            <div class="finding-item ${f.severity}">
                                <div class="finding-header">
                                    <span class="finding-title">${this.escapeHtml(f.title || 'Unknown')}</span>
                                    <span class="finding-severity severity-${f.severity}">${f.severity}</span>
                                </div>
                                <div class="finding-meta">📁 ${this.escapeHtml(f.file_path || '')}:${f.line_start || 0}</div>
                                <div class="finding-description">${this.escapeHtml(f.description || '')}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } else {
                findingsEl.innerHTML = '<p class="text-muted">Keine Findings vorhanden</p>';
            }

            // Scroll to detail
            document.getElementById('activeJobDetail').scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            console.error('[Dashboard] Fehler beim Laden der Job-Details:', error);
        }
    }

    hideJobDetail() {
        document.getElementById('activeJobDetail').style.display = 'none';
    }

    // ─── Export ─────────────────────────────────────────────────────────

    async exportJob(jobId, format) {
        try {
            const res = await fetch(`${this.apiBase}/results/${jobId}`);
            const data = await res.json();

            let content, filename, type;

            if (format === 'json') {
                content = JSON.stringify(data.findings || [], null, 2);
                filename = `glitchhunter-${jobId.slice(0, 8)}.json`;
                type = 'application/json';
            } else if (format === 'md') {
                content = this.findingsToMarkdown(data.findings || []);
                filename = `glitchhunter-${jobId.slice(0, 8)}.md`;
                type = 'text/markdown';
            }

            const blob = new Blob([content], { type });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('[Dashboard] Export-Fehler:', error);
            alert('Export fehlgeschlagen: ' + error.message);
        }
    }

    findingsToMarkdown(findings) {
        let md = `# GlitchHunter Results\n\n`;
        md += `**Total Findings:** ${findings.length}\n\n`;
        md += `## Summary\n`;
        md += `- Critical: ${findings.filter(f => f.severity === 'critical').length}\n`;
        md += `- High: ${findings.filter(f => f.severity === 'high').length}\n`;
        md += `- Medium: ${findings.filter(f => f.severity === 'medium').length}\n`;
        md += `- Low: ${findings.filter(f => f.severity === 'low').length}\n\n`;
        md += `## Findings\n\n`;

        findings.forEach((f, i) => {
            md += `### ${i + 1}. ${f.title || 'Unknown'}\n\n`;
            md += `**Severity:** ${f.severity} | **Confidence:** ${((f.confidence || 0) * 100).toFixed(0)}%\n`;
            md += `**File:** ${f.file_path || 'unknown'}:${f.line_start || 0}\n\n`;
            md += `${f.description || ''}\n\n---\n\n`;
        });

        return md;
    }

    // ─── Helpers ────────────────────────────────────────────────────────

    updateDurations() {
        document.querySelectorAll('.job-duration').forEach(el => {
            const started = el.dataset.started;
            if (started) {
                const diff = Math.floor((Date.now() - new Date(started).getTime()) / 1000);
                el.textContent = diff < 60 ? `${diff}s` : `${Math.floor(diff / 60)}m ${diff % 60}s`;
            }
        });
    }

    shortenPath(path) {
        if (!path) return '';
        const parts = path.split('/');
        return parts.length > 3 ? '...' + parts.slice(-3).join('/') : path;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async refreshJobs() {
        await this.loadJobs();
        await this.loadStats();
    }

    // ─── Folder Browser ────────────────────────────────────────────────

    async openFolderBrowser() {
        const modal = document.getElementById('folderBrowserModal');
        modal.style.display = 'flex';
        await this.browseTo('/home/schaf/projects');
    }

    closeFolderBrowser() {
        document.getElementById('folderBrowserModal').style.display = 'none';
    }

    async browseTo(path) {
        try {
            const res = await fetch(`/api/v1/discover/browse?path=${encodeURIComponent(path)}`);
            const data = await res.json();

            document.getElementById('folderCurrentPath').value = data.path;
            const parentBtn = document.getElementById('folderParentBtn');
            parentBtn.style.display = data.parent ? 'inline-flex' : 'none';
            parentBtn.dataset.parent = data.parent || '';

            const list = document.getElementById('folderList');
            if (data.error) {
                list.innerHTML = `<div class="text-muted text-center py-4">⚠️ ${data.error}</div>`;
                return;
            }

            if (!data.dirs || data.dirs.length === 0) {
                list.innerHTML = '<div class="text-muted text-center py-4">Keine Ordner gefunden</div>';
                return;
            }

            list.innerHTML = data.dirs.map(d => `
                <div class="folder-item ${d.is_project ? 'is-project' : ''}" 
                     onclick="dashboard.browseTo('${d.path.replace(/'/g, "\\'")}')"
                     ondblclick="event.preventDefault(); dashboard.browseTo('${d.path.replace(/'/g, "\\'")}'); dashboard.selectCurrentFolder();">
                    <span class="folder-icon">${d.is_project ? '📦' : '📁'}</span>
                    <span class="folder-name">${d.name}</span>
                    ${d.is_project ? '<span class="folder-badge">Projekt</span>' : ''}
                </div>
            `).join('');
        } catch (error) {
            console.error('[Dashboard] Fehler beim Browse:', error);
        }
    }

    async browseParent() {
        const parent = document.getElementById('folderParentBtn').dataset.parent;
        if (parent) await this.browseTo(parent);
    }

    selectCurrentFolder() {
        const path = document.getElementById('folderCurrentPath').value;
        document.getElementById('repoPath').value = path;
        this.closeFolderBrowser();
    }
}

// Mobile Navigation
function toggleMobileNav() {
    const nav = document.getElementById('mainNav');
    nav?.classList.toggle('active');
}

// Global Instance
const dashboard = new DashboardManager();
