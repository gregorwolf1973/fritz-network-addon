"""HA metrics collector via Supervisor API. Returns InfluxDB 1.x point dicts."""
import logging
import os
from typing import List, Dict, Any
import requests

log = logging.getLogger("homeassistant")

SUPERVISOR_URL = "http://supervisor"
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def _point(measurement: str, tags: Dict[str, str], fields: Dict[str, Any]) -> Dict[str, Any]:
    return {"measurement": measurement, "tags": tags, "fields": fields}


def _get(path: str):
    try:
        r = requests.get(f"{SUPERVISOR_URL}{path}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json().get("data", {})
    except Exception as exc:
        log.warning("Supervisor %s failed: %s", path, exc)
        return None


class HACollector:
    def __init__(self):
        if not TOKEN:
            log.warning("SUPERVISOR_TOKEN empty — HA collector will not work")

    def collect(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        out.extend(self._core_points())
        out.extend(self._host_points())
        out.extend(self._states_points())
        out.extend(self._addon_points())
        return out

    def _core_points(self):
        info = _get("/core/info")
        stats = _get("/core/stats")
        tags: Dict[str, str] = {}
        fields: Dict[str, Any] = {}
        if info:
            fields["running"] = 1 if info.get("state") == "running" else 0
            tags["version"] = info.get("version") or "unknown"
        if stats:
            fields["cpu_percent"] = float(stats.get("cpu_percent", 0) or 0)
            fields["memory_percent"] = float(stats.get("memory_percent", 0) or 0)
            fields["memory_bytes"] = int(stats.get("memory_usage", 0) or 0)
            fields["network_rx"] = int(stats.get("network_rx", 0) or 0)
            fields["network_tx"] = int(stats.get("network_tx", 0) or 0)
        if fields:
            return [_point("ha_core", tags, fields)]
        return []

    def _host_points(self):
        info = _get("/host/info")
        sup = _get("/supervisor/stats")
        fields: Dict[str, Any] = {}
        if info:
            for k in ("disk_total", "disk_used", "disk_free"):
                v = info.get(k)
                if v is not None:
                    fields[f"{k}_gb"] = float(v)
        if sup:
            fields["cpu_percent"] = float(sup.get("cpu_percent", 0) or 0)
            fields["memory_used_bytes"] = int(sup.get("memory_usage", 0) or 0)
            fields["memory_total_bytes"] = int(sup.get("memory_limit", 0) or 0)
        if fields:
            return [_point("ha_host", {}, fields)]
        return []

    def _states_points(self):
        try:
            r = requests.get(f"{SUPERVISOR_URL}/core/api/states", headers=HEADERS, timeout=15)
            r.raise_for_status()
            states = r.json()
        except Exception as exc:
            log.warning("/core/api/states failed: %s", exc)
            return []

        by_domain: Dict[str, int] = {}
        by_state: Dict[str, int] = {}
        for s in states:
            ent_id = s.get("entity_id", "")
            domain = ent_id.split(".", 1)[0] if "." in ent_id else "unknown"
            by_domain[domain] = by_domain.get(domain, 0) + 1
            st = s.get("state", "unknown")
            by_state[st] = by_state.get(st, 0) + 1

        out = [_point("ha_entities", {}, {"total": len(states)})]
        for d, n in by_domain.items():
            out.append(_point("ha_entities_by_domain", {"domain": d}, {"count": n}))
        for st, n in by_state.items():
            out.append(_point("ha_entities_by_state", {"state": st}, {"count": n}))
        return out

    def _addon_points(self):
        data = _get("/addons")
        if data and "addons" in data:
            lst = data["addons"]
            return [_point("ha_addons", {}, {
                "total": len(lst),
                "running": sum(1 for a in lst if a.get("state") == "started"),
            })]
        return []
