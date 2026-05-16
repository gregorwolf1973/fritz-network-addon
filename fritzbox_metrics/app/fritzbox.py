"""FritzBox metrics collector via TR-064. Returns InfluxDB 1.x point dicts."""
import logging
import os
from typing import List, Dict, Any
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzstatus import FritzStatus
from fritzconnection.lib.fritzhosts import FritzHosts
from fritzconnection.lib.fritzwlan import FritzWLAN

log = logging.getLogger("fritzbox")


def _point(measurement: str, tags: Dict[str, str], fields: Dict[str, Any]) -> Dict[str, Any]:
    return {"measurement": measurement, "tags": tags, "fields": fields}


class FritzCollector:
    def __init__(self):
        self.host = os.environ.get("FRITZBOX_HOST", "192.168.178.1")
        self.port = int(os.environ.get("FRITZBOX_PORT", "49000"))
        self.user = os.environ.get("FRITZBOX_USER", "") or None
        self.password = os.environ.get("FRITZBOX_PASSWORD", "") or None
        self._fc = None
        self._status = None
        self._hosts = None

    def _connect(self):
        if self._fc is not None:
            return
        log.info("Connecting to FritzBox %s:%s", self.host, self.port)
        self._fc = FritzConnection(
            address=self.host, port=self.port,
            user=self.user, password=self.password, timeout=10,
        )
        self._status = FritzStatus(fc=self._fc)
        self._hosts = FritzHosts(fc=self._fc)

    def collect(self) -> List[Dict[str, Any]]:
        try:
            self._connect()
        except Exception as exc:
            log.warning("FritzBox connect failed: %s", exc)
            self._fc = None
            return []

        out: List[Dict[str, Any]] = []
        out.extend(self._status_points())
        out.extend(self._host_points())
        out.extend(self._wlan_points())
        return out

    def _status_points(self):
        out = []
        try:
            s = self._status
            fields = {
                "uptime_seconds": int(s.uptime),
                "connected": 1 if s.is_connected else 0,
                "link_up": 1 if s.is_linked else 0,
                "downstream_max_bps": int(s.max_bit_rate[0]),
                "upstream_max_bps": int(s.max_bit_rate[1]),
                "downstream_current_bps": int(s.transmission_rate[1] * 8),
                "upstream_current_bps": int(s.transmission_rate[0] * 8),
                "bytes_sent_total": int(s.bytes_sent),
                "bytes_received_total": int(s.bytes_received),
            }
            try:
                fields["external_ip"] = str(s.external_ip or "unknown")
            except Exception:
                pass
            out.append(_point("fritzbox_wan", {"host": self.host}, fields))
        except Exception as exc:
            log.warning("FritzBox status error: %s", exc)
        return out

    def _host_points(self):
        out = []
        try:
            hosts = self._hosts.get_hosts_info()
            total = len(hosts)
            active = sum(1 for h in hosts if h.get("status"))
            out.append(_point("fritzbox_hosts", {"host": self.host},
                              {"total": total, "active": active}))
        except Exception as exc:
            log.warning("FritzBox hosts error: %s", exc)
        return out

    def _wlan_points(self):
        out = []
        band_map = {1: "2.4GHz", 2: "5GHz", 3: "5GHz-2", 4: "guest"}
        for idx, band in band_map.items():
            try:
                wlan = FritzWLAN(fc=self._fc, service=idx)
                out.append(_point(
                    "fritzbox_wlan",
                    {"host": self.host, "band": band},
                    {"clients": int(wlan.host_number),
                     "enabled": 1 if wlan.is_enabled else 0},
                ))
            except Exception:
                pass
        return out
