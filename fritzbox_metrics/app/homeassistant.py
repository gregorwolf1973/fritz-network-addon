"""Home Assistant metrics collector via Supervisor API. Returns InfluxDB Points."""
import logging
import os
from typing import List
import requests
from influxdb_client import Point

log = logging.getLogger("homeassistant")

SUPERVISOR_URL = "http://supervisor"
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


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

    def collect(self) -> List[Point]:
        points: List[Point] = []
        points.extend(self._core_points())
        points.extend(self._host_points())
        points.extend(self._states_points())
        points.extend(self._addon_points())
        return points

    def _core_points(self) -> List[Point]:
        out: List[Point] = []
        info = _get("/core/info")
        stats = _get("/core/stats")
        p = Point("ha_core")
        any_field = False
        if info:
            p.field("running", 1 if info.get("state") == "running" else 0)
            p.tag("version", info.get("version") or "unknown")
            any_field = True
        if stats:
            p.field("cpu_percent", float(stats.get("cpu_percent", 0) or 0))
            p.field("memory_percent", float(stats.get("memory_percent", 0) or 0))
            p.field("memory_bytes", int(stats.get("memory_usage", 0) or 0))
            p.field("network_rx", int(stats.get("network_rx", 0) or 0))
            p.field("network_tx", int(stats.get("network_tx", 0) or 0))
            any_field = True
        if any_field:
            out.append(p)
        return out

    def _host_points(self) -> List[Point]:
        out: List[Point] = []
        info = _get("/host/info")
        sup = _get("/supervisor/stats")
        p = Point("ha_host")
        any_field = False
        if info:
            for k_src, k_dst in (("disk_total", "disk_total_gb"),
                                 ("disk_used", "disk_used_gb"),
                                 ("disk_free", "disk_free_gb")):
                v = info.get(k_src)
                if v is not None:
                    p.field(k_dst, float(v))
                    any_field = True
        if sup:
            p.field("cpu_percent", float(sup.get("cpu_percent", 0) or 0))
            p.field("memory_used_bytes", int(sup.get("memory_usage", 0) or 0))
            p.field("memory_total_bytes", int(sup.get("memory_limit", 0) or 0))
            any_field = True
        if any_field:
            out.append(p)
        return out

    def _states_points(self) -> List[Point]:
        try:
            r = requests.get(f"{SUPERVISOR_URL}/core/api/states", headers=HEADERS, timeout=15)
            r.raise_for_status()
            states = r.json()
        except Exception as exc:
            log.warning("/core/api/states failed: %s", exc)
            return []

        by_domain: dict[str, int] = {}
        by_state: dict[str, int] = {}
        for s in states:
            ent_id = s.get("entity_id", "")
            domain = ent_id.split(".", 1)[0] if "." in ent_id else "unknown"
            by_domain[domain] = by_domain.get(domain, 0) + 1
            st = s.get("state", "unknown")
            by_state[st] = by_state.get(st, 0) + 1

        out: List[Point] = [Point("ha_entities").field("total", len(states))]
        for d, n in by_domain.items():
            out.append(Point("ha_entities_by_domain").tag("domain", d).field("count", n))
        for st, n in by_state.items():
            out.append(Point("ha_entities_by_state").tag("state", st).field("count", n))
        return out

    def _addon_points(self) -> List[Point]:
        out: List[Point] = []
        data = _get("/addons")
        if data and "addons" in data:
            lst = data["addons"]
            out.append(Point("ha_addons")
                       .field("total", len(lst))
                       .field("running", sum(1 for a in lst if a.get("state") == "started")))
        return out
