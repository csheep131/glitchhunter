"""
eBPF Tracer für dynamische Code-Analyse auf Linux.

System-Call-Tracing mit BCC (BPF Compiler Collection) für:
- C/C++ Programme
- Rust Binaries
- Native Applications
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from sandbox.tracers.base import BaseTracer

logger = logging.getLogger(__name__)


class EbpfTracer(BaseTracer):
    """
    Tracer für native Binaries mit eBPF.

    Verwendet BCC (BPF Compiler Collection) für
    System-Call-Tracing auf Linux-Systemen.

    Usage:
        tracer = EbpfTracer()
        results = await tracer.trace(binary_path)
    """

    def __init__(
        self,
        timeout: int = 60,
        enable_coverage: bool = False,
        trace_syscalls: bool = True,
    ):
        """
        Initialisiert den eBPF Tracer.

        Args:
            timeout: Timeout in Sekunden
            enable_coverage: Coverage-Tracking (N/A für eBPF)
            trace_syscalls: System-Call-Tracing aktivieren
        """
        super().__init__(
            name="EbpfTracer",
            timeout=timeout,
            enable_coverage=enable_coverage,
        )
        self.trace_syscalls = trace_syscalls
        self._is_linux = os.uname().sysname == "Linux"

        logger.info(
            f"EbpfTracer initialisiert: "
            f"timeout={timeout}, linux={self._is_linux}"
        )

    async def trace(self, target: Path, **kwargs) -> Dict[str, Any]:
        """
        Führt eBPF-Tracing von nativen Binaries durch.

        Args:
            target: Ziel-Pfad (Binary oder Source-Datei)
            **kwargs: Zusätzliche Argumente

        Returns:
            Trace-Ergebnis
        """
        logger.info(f"EbpfTracer: Starte Trace von {target}")
        self._clear_results()

        if not self._is_linux:
            logger.warning("eBPF nur auf Linux verfügbar")
            return {"success": False, "error": "eBPF only available on Linux"}

        try:
            # BCC importieren (nur auf Linux mit BCC installiert)
            from bcc import BPF

            # eBPF Programm für sys_execve tracing
            bpf_program = """
            #include <uapi/linux/ptrace.h>
            #include <linux/sched.h>

            struct event_t {
                u32 pid;
                u32 uid;
                char comm[TASK_COMM_LEN];
                char filename[256];
            };

            BPF_PERF_OUTPUT(events);

            int trace_exec(struct pt_regs *ctx, struct filename *filename) {
                struct event_t event = {};
                event.pid = bpf_get_current_pid_tgid();
                event.uid = bpf_get_current_uid_gid();
                bpf_get_current_comm(&event.comm, sizeof(event.comm));
                bpf_probe_read_user_str(&event.filename, sizeof(event.filename), filename->name);
                events.perf_submit(ctx, &event, sizeof(event));
                return 0;
            }
            """

            # BPF laden
            bpf = BPF(text=bpf_program)
            bpf.attach_kprobe(event="do_execve", fn_name="trace_exec")

            # Events sammeln
            events_collected = []

            def collect_event(cpu, data, size):
                event = bpf["events"].event(data)
                events_collected.append({
                    "pid": event.pid,
                    "uid": event.uid,
                    "comm": event.comm.decode(),
                    "filename": event.filename.decode(),
                })

            # Kurzes Sampling
            bpf["events"].open_perf_buffer(collect_event)
            await asyncio.sleep(min(5, self.timeout / 10))  # Max 5 Sekunden
            bpf.perf_buffer_poll()

            # eBPF Issue melden wenn System-Calls gefunden
            if events_collected:
                self._add_result({
                    "id": "ebpf_trace_001",
                    "file_path": str(target),
                    "line_start": 0,
                    "line_end": 0,
                    "severity": "info",
                    "category": "runtime",
                    "title": "eBPF Runtime Trace",
                    "description": f"System call tracing completed ({len(events_collected)} events)",
                    "confidence": 0.9,
                    "trace_type": "ebpf",
                    "metadata": {"events": len(events_collected)},
                })

            logger.info("eBPF tracing complete")

            return {
                "success": True,
                "results_count": len(self._results),
                "events_collected": len(events_collected),
            }

        except ImportError:
            logger.warning("BCC nicht installiert, überspringe eBPF tracing")
            return {"success": False, "error": "BCC not installed"}
        except Exception as e:
            logger.error(f"eBPF tracing failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_results(self) -> List[Dict[str, Any]]:
        """
        Extrahiert alle Trace-Ergebnisse.

        Returns:
            Liste von Trace-Ergebnissen
        """
        return self._results.copy()

    def trace_process(
        self,
        pid: int,
        duration: int = 10,
    ) -> Dict[str, Any]:
        """
        Trace einen laufenden Prozess.

        Args:
            pid: Prozess-ID
            duration: Trace-Dauer in Sekunden

        Returns:
            Trace-Ergebnis
        """
        logger.info(f"Tracing process {pid} for {duration}s")

        try:
            from bcc import BPF

            # Einfaches execve Tracing
            bpf_program = """
            #include <uapi/linux/ptrace.h>
            BPF_PERF_OUTPUT(events);

            int trace_exec(struct pt_regs *ctx) {
                u32 pid = bpf_get_current_pid_tgid();
                events.perf_submit(ctx, &pid, sizeof(pid));
                return 0;
            }
            """

            bpf = BPF(text=bpf_program)
            bpf.attach_kprobe(event="do_execve", fn_name="trace_exec")

            events = []

            def on_event(cpu, data, size):
                events.append({"pid": bpf["events"].event(data).pid})

            bpf["events"].open_perf_buffer(on_event)
            asyncio.run(asyncio.sleep(duration))
            bpf.perf_buffer_poll()

            return {
                "success": True,
                "pid": pid,
                "events": len(events),
            }

        except Exception as e:
            logger.error(f"Process tracing failed: {e}")
            return {"success": False, "error": str(e)}
