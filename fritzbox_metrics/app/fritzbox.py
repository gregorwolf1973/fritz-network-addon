"""FritzBox metrics collector via TR-064. Returns InfluxDB Points."""
import logging
import os
from typing import List
from influxdb_client import Point
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzstatus import FritzStatus
from fritzconnection.lib.fritzhosts import FritzHosts
from fritzconnection.lib.fritzwlan import FritzWLAN

log = logging.getLogger("fritzbox")


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

    def collect(self) -> List[Point]:
        try:
            self._connect()
        except Exception as exc:
            log.warning("FritzBox connect failed: %s", exc)
            self._fc = None
            return []

        points: List[Point] = []
        points.extend(self._status_points())
        points.extend(self._host_points())
        points.extend(self._wlan_points())
        return points

    def _status_points(self) -> List[Point]:
        out: List[Point] = []
        try:
            s = self._status
            p = (Point("fritzbox_wan")
                 .tag("host", self.host)
                 .field("uptime_seconds", int(s.uptime))
                 .field("connected", 1 if s.is_connected else 0)
                 .field("link_up", 1 if s.is_linked else 0)
                 .field("downstream_max_bps", int(s.max_bit_rate[0]))
                 .field("upstream_max_bps", int(s.max_bit_rate[1]))
                 .field("downstream_current_bps", int(s.transmission_rate[1] * 8))
                 .field("upstream_current_bps", int(s.transmission_rate[0] * 8))
                 .field("bytes_sent_total", int(s.bytes_sent))
                 .field("bytes_received_total", int(s.bytes_received)))
            try:
                p.field("external_ip", str(s.external_ip or "unknown"))
            except Exception:
                pass
            out.append(p)
        except Exception as exc:
            log.warning("FritzBox status error: %s", exc)
        return out

    def _host_points(self) -> List[Point]:
        out: List[Point] = []
        try:
            hosts = self._hosts.get_hosts_info()
            total = len(hosts)
            active = sum(1 for h in hosts if h.get("status"))
            out.append(Point("fritzbox_hosts")
                       .tag("host", self.host)
                       .field("total", total)
                       .field("active", active))
        except Exception as exc:
            log.warning("FritzBox hosts error: %s", exc)
        return out

    def _wlan_points(self) -> List[Point]:
        out: List[Point] = []
        band_map = {1: "2.4GHz", 2: "5GHz", 3: "5GHz-2", 4: "guest"}
        for idx, band in band_map.items():
            try:
                wlan = FritzWLAN(fc=self._fc, service=idx)
                out.append(Point("fritzbox_wlan")
                           .tag("host", self.host)
                           .tag("band", band)
                           .field("clients", int(wlan.host_number))
                           .field("enabled", 1 if wlan.is_enabled else 0))
            except Exception:
                pass
        return out
