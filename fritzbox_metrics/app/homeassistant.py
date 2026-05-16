"""Home Assistant metrics collector via Supervisor API.

Inside an HA addon, http://supervisor is reachable when `hassio_api: true`
and the SUPERVISOR_TOKEN env var is auto-injected by the Supervisor.
"""
import logging
import os
import requests
from prometheus_client import Gauge, Counter

log = logging.getLogger("homeassistant")

SUPERVISOR_URL = "http://supervisor"
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# ── Core (HA itself) ────────────────────────────────────────────────────────
g_core_cpu = Gauge("ha_core_cpu_percent", "HA Core CPU usage")
g_core_mem = Gauge("ha_core_memory_percent", "HA Core memory percent")
g_core_mem_used = Gauge("ha_core_memory_bytes", "HA Core memory bytes used")
g_core_net_rx = Gauge("ha_core_network_rx_bytes", "HA Core RX bytes")
g_core_net_tx = Gauge("ha_core_network_tx_bytes", "HA Core TX bytes")
g_core_state = Gauge("ha_core_running", "1 if HA Core is running")
g_core_version_info = Gauge("ha_core_version_info", "HA Core version", ["version"])

# ── Supervisor host ─────────────────────────────────────────────────────────
g_host_cpu = Gauge("ha_host_cpu_percent", "Host CPU percent")
g_host_mem_used = Gauge("ha_host_memory_used_bytes", "Host memory used")
g_host_mem_total = Gauge("ha_host_memory_total_bytes", "Host memory total")
g_host_disk_used = Gauge("ha_host_disk_used_bytes", "Host disk used")
g_host_disk_total = Gauge("ha_host_disk_total_bytes", "Host disk total")
g_host_disk_free = Gauge("ha_host_disk_free_bytes", "Host disk free")

# ── Entities / states ───────────────────────────────────────────────────────
g_entity_count = Gauge("ha_entities_total", "Number of entities", ["domain"])
g_entity_state_counts = Gauge("ha_entity_state_total", "Entity count by state", ["state"])

# ── Addons ──────────────────────────────────────────────────────────────────
g_addons_total = Gauge("ha_addons_total", "Number of installed addons")
g_addons_running = Gauge("ha_addons_running", "Number of running addons")

c_errors = Counter("ha_collect_errors_total", "HA collector errors", ["source"])


def _get(path: str):
    try:
        r = requests.get(f"{SUPERVISOR_URL}{path}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json().get("data", {})
    except Exception as exc:
        log.warning("Supervisor %s failed: %s", path, exc)
        c_errors.labels(source=path).inc()
        return None


class HACollector:
    def __init__(self):
        if not TOKEN:
            log.warning("SUPERVISOR_TOKEN is empty — HA collector will not work")

    def collect(self):
        self._collect_core()
        self._collect_host()
        self._collect_states()
        self._collect_addons()

    def _collect_core(self):
        info = _get("/core/info")
        if info:
            g_core_state.set(1 if info.get("state") == "running" else 0)
            v = info.get("version") or "unknown"
            g_core_version_info.clear()
            g_core_version_info.labels(version=v).set(1)

        stats = _get("/core/stats")
        if stats:
            g_core_cpu.set(stats.get("cpu_percent", 0))
            g_core_mem.set(stats.get("memory_percent", 0))
            g_core_mem_used.set(stats.get("memory_usage", 0))
            g_core_net_rx.set(stats.get("network_rx", 0))
            g_core_net_tx.set(stats.get("network_tx", 0))

    def _collect_host(self):
        info = _get("/host/info")
        if info:
            disk_total = info.get("disk_total")
            disk_used = info.get("disk_used")
            disk_free = info.get("disk_free")
            if disk_total is not None:
                g_host_disk_total.set(float(disk_total) * 1024**3)
            if disk_used is not None:
                g_host_disk_used.set(float(disk_used) * 1024**3)
            if disk_free is not None:
                g_host_disk_free.set(float(disk_free) * 1024**3)

        stats = _get("/supervisor/stats")
        if stats:
            g_host_cpu.set(stats.get("cpu_percent", 0))
            g_host_mem_used.set(stats.get("memory_usage", 0))
            g_host_mem_total.set(stats.get("memory_limit", 0))

    def _collect_states(self):
        """Pulls entity states from the HA Core REST API."""
        try:
            r = requests.get(
                f"{SUPERVISOR_URL}/core/api/states",
                headers=HEADERS,
                timeout=15,
            )
            r.raise_for_status()
            states = r.json()
        except Exception as exc:
            log.warning("Core /api/states failed: %s", exc)
            c_errors.labels(source="/core/api/states").inc()
            return

        by_domain: dict[str, int] = {}
        by_state: dict[str, int] = {}
        for s in states:
            ent_id = s.get("entity_id", "")
            domain = ent_id.split(".", 1)[0] if "." in ent_id else "unknown"
            by_domain[domain] = by_domain.get(domain, 0) + 1
            st = s.get("state", "unknown")
            by_state[st] = by_state.get(st, 0) + 1

        g_entity_count.clear()
        for d, n in by_domain.items():
            g_entity_count.labels(domain=d).set(n)
        g_entity_state_counts.clear()
        for st, n in by_state.items():
            g_entity_state_counts.labels(state=st).set(n)

    def _collect_addons(self):
        addons = _get("/addons")
        if addons and "addons" in addons:
            lst = addons["addons"]
            g_addons_total.set(len(lst))
            g_addons_running.set(sum(1 for a in lst if a.get("state") == "started"))
