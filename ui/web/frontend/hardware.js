/**
 * GlitchHunter Web-UI - Hardware-Monitoring Manager
 */

class HardwareManager {
    constructor() {
        this.apiBase = '/api/v1/hardware';
        this.chart = null;
        this.updateInterval = null;
        
        this.init();
    }

    init() {
        console.log('[Hardware] Initialisiere...');
        this.loadHardware();
        this.loadHistory();
        
        // Alle 2s aktualisieren
        this.updateInterval = setInterval(() => {
            this.loadHardware();
        }, 2000);
    }

    async loadHardware() {
        try {
            const response = await fetch(`${this.apiBase}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            // GPU
            if (data.gpu && data.gpu.available) {
                document.getElementById('gpuName').textContent = data.gpu.name;
                document.getElementById('gpuUsage').textContent = `${data.gpu.usage.toFixed(1)}%`;
                document.getElementById('gpuUsageBar').style.width = `${data.gpu.usage}%`;
                document.getElementById('gpuVram').textContent = `${data.gpu.vram_used} / ${data.gpu.vram_total} MB`;
                document.getElementById('gpuVramBar').style.width = `${(data.gpu.vram_used / data.gpu.vram_total) * 100}%`;
                document.getElementById('gpuTemp').textContent = `${data.gpu.temperature}°C`;
                document.getElementById('gpuPower').textContent = `${data.gpu.power_draw.toFixed(1)} W`;
                document.getElementById('gpuStatus').className = 'status-indicator ok';
            } else {
                document.getElementById('gpuName').textContent = data.gpu?.error || 'Nicht verfügbar';
                document.getElementById('gpuStatus').className = 'status-indicator error';
            }

            // CPU
            document.getElementById('cpuName').textContent = data.cpu.model || 'Unknown';
            document.getElementById('cpuUsage').textContent = `${data.cpu.usage.toFixed(1)}%`;
            document.getElementById('cpuUsageBar').style.width = `${data.cpu.usage}%`;
            document.getElementById('cpuCores').textContent = data.cpu.cores;
            document.getElementById('cpuTemp').textContent = `${data.cpu.temperature}°C`;
            document.getElementById('cpuFreq').textContent = `${data.cpu.frequency_mhz.toFixed(0)} MHz`;

            // RAM
            document.getElementById('ramUsage').textContent = `${data.memory.used} / ${data.memory.total} MB`;
            document.getElementById('ramBar').style.width = `${data.memory.percent}%`;
            document.getElementById('ramPercent').textContent = `${data.memory.percent.toFixed(1)}%`;
            document.getElementById('swapUsage').textContent = `${data.memory.swap_percent.toFixed(1)}%`;

            // Alerts laden
            this.loadAlerts();

        } catch (error) {
            console.error('[Hardware] Fehler beim Laden:', error);
        }
    }

    async loadAlerts() {
        try {
            const response = await fetch(`${this.apiBase}/alerts`);
            if (!response.ok) return;
            
            const alerts = await response.json();
            const container = document.getElementById('alertsContainer');
            
            if (alerts.length === 0) {
                container.innerHTML = '';
                return;
            }
            
            container.innerHTML = alerts.map(alert => `
                <div class="alert alert-${alert.level}">
                    ⚠️ ${alert.message}
                </div>
            `).join('');

        } catch (error) {
            console.error('[Hardware] Fehler beim Laden der Alerts:', error);
        }
    }

    async loadHistory() {
        try {
            const response = await fetch(`${this.apiBase}/history?minutes=5`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const history = await response.json();
            this.renderChart(history);

        } catch (error) {
            console.error('[Hardware] Fehler beim Laden der Historie:', error);
        }
    }

    renderChart(history) {
        const ctx = document.getElementById('historyChart');
        if (!ctx) return;

        const labels = history.map(h => new Date(h.timestamp).toLocaleTimeString());
        
        const data = {
            labels: labels,
            datasets: [
                {
                    label: 'GPU Auslastung',
                    data: history.map(h => h.gpu_usage),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                },
                {
                    label: 'CPU Auslastung',
                    data: history.map(h => h.cpu_usage),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                },
                {
                    label: 'RAM Verbrauch',
                    data: history.map(h => h.memory_percent),
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4,
                },
            ]
        };

        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(ctx, {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: '%',
                        },
                    },
                },
            },
        });
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

// Globale Instanz
let hardwareManager;

// Initialisierung
document.addEventListener('DOMContentLoaded', () => {
    hardwareManager = new HardwareManager();
});

// Cleanup beim Verlassen
window.addEventListener('beforeunload', () => {
    if (hardwareManager) {
        hardwareManager.destroy();
    }
});
