"""
Hardware-Monitoring Manager für GlitchHunter Web-UI.

Überwacht Hardware-Ressourcen in Echtzeit:
- GPU (Auslastung, VRAM, Temperatur, Power)
- CPU (Auslastung, Kerne, Temperatur)
- RAM (Verbrauch, Verfügbar, Swap)

Features:
- PyNVML für NVIDIA-GPUs
- psutil für CPU/RAM
- WebSocket für Live-Updates
- Historie-Daten
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """GPU-Informationen."""
    name: str = ""
    usage: float = 0.0  # %
    vram_total: int = 0  # MB
    vram_used: int = 0  # MB
    vram_free: int = 0  # MB
    temperature: float = 0.0  # °C
    power_draw: float = 0.0  # W
    power_limit: float = 0.0  # W
    fan_speed: int = 0  # %
    compute_mode: str = ""
    available: bool = False
    error: Optional[str] = None


@dataclass
class CPUInfo:
    """CPU-Informationen."""
    model: str = ""
    cores_physical: int = 0
    cores_logical: int = 0
    usage: float = 0.0  # %
    frequency_mhz: float = 0.0
    temperature: float = 0.0  # °C
    per_core_usage: List[float] = field(default_factory=list)


@dataclass
class MemoryInfo:
    """RAM-Informationen."""
    total: int = 0  # MB
    used: int = 0  # MB
    free: int = 0  # MB
    percent: float = 0.0  # %
    swap_total: int = 0  # MB
    swap_used: int = 0  # MB
    swap_free: int = 0  # MB
    swap_percent: float = 0.0  # %


@dataclass
class HardwareSnapshot:
    """Hardware-Snapshot zu einem Zeitpunkt."""
    timestamp: datetime = field(default_factory=datetime.now)
    gpu: Optional[GPUInfo] = None
    cpu: Optional[CPUInfo] = None
    memory: Optional[MemoryInfo] = None


class HardwareMonitor:
    """
    Monitor für Hardware-Ressourcen.
    
    Features:
    - GPU-Monitoring (NVIDIA via PyNVML)
    - CPU-Monitoring (via psutil)
    - RAM-Monitoring (via psutil)
    - WebSocket-Support für Live-Updates
    - Snapshot-Historie
    
    Usage:
        monitor = HardwareMonitor()
        monitor.initialize()
        snapshot = monitor.get_snapshot()
    """
    
    def __init__(self):
        """Initialisiert Hardware-Monitor."""
        self._nvml_available: bool = False
        self._snapshots: List[HardwareSnapshot] = []
        self._max_snapshots: int = 300  # 5 Minuten bei 1s Intervall
        self._monitoring: bool = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        logger.info("HardwareMonitor initialisiert")
    
    def initialize(self):
        """Initialisiert Monitoring-Komponenten."""
        logger.info("Initialisiere Hardware-Monitoring...")
        
        # PyNVML für GPU-Monitoring
        try:
            import pynvml
            
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            if device_count > 0:
                self._nvml_available = True
                logger.info(f"PyNVML initialisiert: {device_count} GPU(s) gefunden")
            else:
                logger.warning("Keine NVIDIA-GPUs gefunden")
                
        except ImportError:
            logger.warning("PyNVML nicht installiert - GPU-Monitoring nicht verfügbar")
        except Exception as e:
            logger.warning(f"PyNVML-Initialisierung fehlgeschlagen: {e}")
    
    def get_gpu_info(self) -> GPUInfo:
        """
        Holt GPU-Informationen.
        
        Returns:
            GPUInfo
        """
        info = GPUInfo()
        
        if not self._nvml_available:
            info.available = False
            info.error = "PyNVML nicht verfügbar"
            return info
        
        try:
            import pynvml
            
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # Basis-Infos
            info.name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(info.name, bytes):
                info.name = info.name.decode('utf-8')
            
            # Auslastung
            info.usage = float(pynvml.nvmlDeviceGetUtilizationRates(handle).gpu)
            
            # VRAM
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info.vram_total = memory.total // (1024 * 1024)
            info.vram_used = memory.used // (1024 * 1024)
            info.vram_free = memory.free // (1024 * 1024)
            
            # Temperatur
            info.temperature = float(pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            ))
            
            # Power
            try:
                power = pynvml.nvmlDeviceGetPowerUsage(handle)
                info.power_draw = float(power) / 1000  # W
                power_limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle)
                info.power_limit = float(power_limit) / 1000  # W
            except pynvml.NVMLError:
                pass
            
            # Fan-Speed
            try:
                info.fan_speed = int(pynvml.nvmlDeviceGetFanSpeed(handle))
            except pynvml.NVMLError:
                pass
            
            info.available = True
            
        except Exception as e:
            logger.error(f"Fehler beim GPU-Monitoring: {e}")
            info.available = False
            info.error = str(e)
        
        return info
    
    def get_cpu_info(self) -> CPUInfo:
        """
        Holt CPU-Informationen.
        
        Returns:
            CPUInfo
        """
        info = CPUInfo()
        
        try:
            import psutil
            
            # Modell
            info.model = psutil.cpu_freq()
            
            # Kerne
            info.cores_physical = psutil.cpu_count(logical=False)
            info.cores_logical = psutil.cpu_count(logical=True)
            
            # Auslastung
            info.usage = psutil.cpu_percent(interval=0.1)
            info.per_core_usage = psutil.cpu_percent(interval=0.1, percpu=True)
            
            # Frequenz
            freq = psutil.cpu_freq()
            if freq:
                info.frequency_mhz = float(freq.current)
            
            # Temperatur (wenn verfügbar)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            if 'cpu' in entry.label.lower() or 'core' in entry.label.lower():
                                info.temperature = float(entry.current)
                                break
            except Exception:
                pass
            
        except ImportError:
            logger.warning("psutil nicht installiert - CPU-Monitoring eingeschränkt")
        except Exception as e:
            logger.error(f"Fehler beim CPU-Monitoring: {e}")
        
        return info
    
    def get_memory_info(self) -> MemoryInfo:
        """
        Holt RAM-Informationen.
        
        Returns:
            MemoryInfo
        """
        info = MemoryInfo()
        
        try:
            import psutil
            
            # RAM
            mem = psutil.virtual_memory()
            info.total = mem.total // (1024 * 1024)
            info.used = mem.used // (1024 * 1024)
            info.free = mem.available // (1024 * 1024)
            info.percent = float(mem.percent)
            
            # Swap
            swap = psutil.swap_memory()
            info.swap_total = swap.total // (1024 * 1024)
            info.swap_used = swap.used // (1024 * 1024)
            info.swap_free = swap.free // (1024 * 1024)
            info.swap_percent = float(swap.percent)
            
        except ImportError:
            logger.warning("psutil nicht installiert - RAM-Monitoring nicht verfügbar")
        except Exception as e:
            logger.error(f"Fehler beim RAM-Monitoring: {e}")
        
        return info
    
    def get_snapshot(self) -> HardwareSnapshot:
        """
        Erstellt Hardware-Snapshot.
        
        Returns:
            HardwareSnapshot
        """
        snapshot = HardwareSnapshot(
            timestamp=datetime.now(),
            gpu=self.get_gpu_info(),
            cpu=self.get_cpu_info(),
            memory=self.get_memory_info(),
        )
        
        # Snapshot speichern (für Historie)
        self._snapshots.append(snapshot)
        
        # Alte Snapshots löschen
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
        
        return snapshot
    
    def get_hardware_summary(self) -> Dict[str, Any]:
        """
        Returns Hardware-Zusammenfassung.
        
        Returns:
            Dict mit Hardware-Infos
        """
        gpu = self.get_gpu_info()
        cpu = self.get_cpu_info()
        memory = self.get_memory_info()
        
        return {
            "gpu": {
                "name": gpu.name,
                "available": gpu.available,
                "usage": gpu.usage,
                "vram_used": gpu.vram_used,
                "vram_total": gpu.vram_total,
                "temperature": gpu.temperature,
            } if gpu.available else {"available": False, "error": gpu.error},
            "cpu": {
                "model": cpu.model,
                "cores": cpu.cores_logical,
                "usage": cpu.usage,
                "temperature": cpu.temperature,
            },
            "memory": {
                "total": memory.total,
                "used": memory.used,
                "percent": memory.percent,
                "swap_percent": memory.swap_percent,
            },
        }
    
    def get_history(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """
        Returns Historie der Snapshots.
        
        Args:
            minutes: Minuten an Historie
            
        Returns:
            Liste von Snapshots
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        return [
            {
                "timestamp": s.timestamp.isoformat(),
                "gpu_usage": s.gpu.usage if s.gpu and s.gpu.available else 0,
                "gpu_vram": s.gpu.vram_used if s.gpu and s.gpu.available else 0,
                "gpu_temp": s.gpu.temperature if s.gpu and s.gpu.available else 0,
                "cpu_usage": s.cpu.usage if s.cpu else 0,
                "memory_percent": s.memory.percent if s.memory else 0,
            }
            for s in self._snapshots
            if s.timestamp >= cutoff
        ]
    
    async def start_monitoring(self, interval: float = 1.0):
        """
        Startet kontinuierliches Monitoring.
        
        Args:
            interval: Intervall in Sekunden
        """
        self._monitoring = True
        
        while self._monitoring:
            self.get_snapshot()
            await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stoppt kontinuierliches Monitoring."""
        self._monitoring = False
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """
        Returns Hardware-Alarme.
        
        Returns:
            Liste von Alarmen
        """
        alerts = []
        
        gpu = self.get_gpu_info()
        cpu = self.get_cpu_info()
        memory = self.get_memory_info()
        
        # GPU-Temperatur
        if gpu.available and gpu.temperature > 85:
            alerts.append({
                "level": "warning",
                "component": "gpu",
                "message": f"GPU-Temperatur hoch: {gpu.temperature}°C",
            })
        
        if gpu.available and gpu.temperature > 95:
            alerts.append({
                "level": "critical",
                "component": "gpu",
                "message": f"GPU-Temperatur kritisch: {gpu.temperature}°C",
            })
        
        # CPU-Temperatur
        if cpu.temperature > 85:
            alerts.append({
                "level": "warning",
                "component": "cpu",
                "message": f"CPU-Temperatur hoch: {cpu.temperature}°C",
            })
        
        # RAM-Verbrauch
        if memory.percent > 90:
            alerts.append({
                "level": "warning",
                "component": "memory",
                "message": f"RAM-Verbrauch hoch: {memory.percent}%",
            })
        
        if memory.percent > 95:
            alerts.append({
                "level": "critical",
                "component": "memory",
                "message": f"RAM-Verbrauch kritisch: {memory.percent}%",
            })
        
        return alerts


# ============== Globale Instanz ==============

_hardware_monitor: Optional[HardwareMonitor] = None


def get_hardware_monitor() -> HardwareMonitor:
    """
    Returns globale HardwareMonitor-Instanz.
    
    Returns:
        HardwareMonitor
    """
    global _hardware_monitor
    if _hardware_monitor is None:
        _hardware_monitor = HardwareMonitor()
        _hardware_monitor.initialize()
    return _hardware_monitor
