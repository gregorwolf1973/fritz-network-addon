"""FritzBox metrics collector via TR-064."""
import logging
import os
from prometheus_client import Gauge, Counter
from fritzconnection import FritzConnection
from fritzconnection.lib.fritzstatus import FritzStatus
from fritzconnection.lib.fritzhosts import FritzHosts
from fritzconnection.lib.fritzwlan import FritzWLAN

log = logging.getLogger("fritzbox")

LABELS = ["host"]

# ── DSL / WAN ───────────────────────────────────────────────────────────────
g_up = Gauge("fritzbox_uptime_seconds", "FritzBox uptime", LABELS)
g_connected = Gauge("fritzbox_connected", "1 if WAN connected", LABELS)
g_link_up = Gauge("fritzbox_link_up", "1 if physical link is up", LABELS)
g_ext_ip = Gauge("fritzbox_external_ip_info", "External IP (label only)", LABELS + ["ip"])

g_dl_max = Gauge("fritzbox_downstream_max_bps", "Max downstream bit/s", LABELS)
g_ul_max = Gauge("fritzbox_upstream_max_bps", "Max upstream bit/s", LABELS)
g_dl_cur = Gauge("fritzbox_downstream_current_bps", "Current downstream bit/s", LABELS)
g_ul_cur = Gauge("fritzbox_upstream_current_bps", "Current upstream bit/s", LABELS)

c_bytes_sent = Counter("fritzbox_bytes_sent_total", "Total bytes sent (WAN)", LABELS)
c_bytes_recv = Counter("fritzbox_bytes_received_total", "Total bytes received (WAN)", LABELS)

# ── Hosts ───────────────────────────────────────────────────────────────────
g_hosts_total = Gauge("fritzbox_hosts_total", "Number of known hosts", LABELS)
g_hosts_active = Gauge("fritzbox_hosts_active", "Active hosts", LABELS)

# ── WLAN ────────────────────────────────────────────────────────────────────
g_wlan_clients = Gauge("fritzbox_wlan_clients", "WLAN clients per band", LABELS + ["band"])
g_wlan_enabled = Gauge("fritzbox_wlan_enabled", "WLAN enabled per band", LABELS + ["band"])

# ── Up/down events ──────────────────────────────────────────────────────────
g_collect_errors = Counter("fritzbox_collect_errors_total", "Collector errors", LABELS + ["source"])


class FritzCollector:
    def __init__(self):
        self.host = os.environ.get("FRITZBOX_HOST", "192.168.178.1")
        self.port = int(os.environ.get("FRITZBOX_PORT", "49000"))
        self.user = os.environ.get("FRITZBOX_USER", "") or None
        self.password = os.environ.get("FRITZBOX_PASSWORD", "") or None
        self.label = {"host": self.host}
        self._fc = None
        self._status = None
        self._hosts = None
        self._last_sent = None
        self._last_recv = None

    def _connect(self):
        if self._fc is not None:
            return
        log.info("Connecting to FritzBox %s:%s", self.host, self.port)
        self._fc = FritzConnection(
            address=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            timeout=10,
        )
        self._status = FritzStatus(fc=self._fc)
        self._hosts = FritzHosts(fc=self._fc)

    def _err(self, source: str, exc: Exception):
        log.warning("FritzBox %s error: %s", source, exc)
        g_collect_errors.labels(**self.label, source=source).inc()

    def collect(self):
        try:
            self._connect()
        except Exception as exc:
            self._err("connect", exc)
            self._fc = None
            return

        self._collect_status()
        self._collect_hosts()
        self._collect_wlan()

    def _collect_status(self):
        try:
            s = self._status
            g_up.labels(**self.label).set(s.uptime)
            g_connected.labels(**self.label).set(1 if s.is_connected else 0)
            g_link_up.labels(**self.label).set(1 if s.is_linked else 0)

            g_dl_max.labels(**self.label).set(s.max_bit_rate[0])
            g_ul_max.labels(**self.label).set(s.max_bit_rate[1])
            g_dl_cur.labels(**self.label).set(s.transmission_rate[1] * 8)
            g_ul_cur.labels(**self.label).set(s.transmission_rate[0] * 8)

            sent = s.bytes_sent
            recv = s.bytes_received
            if self._last_sent is not None and sent >= self._last_sent:
                c_bytes_sent.labels(**self.label).inc(sent - self._last_sent)
            if self._last_recv is not None and recv >= self._last_recv:
                c_bytes_recv.labels(**self.label).inc(recv - self._last_recv)
            self._last_sent, self._last_recv = sent, recv

            try:
                ip = s.external_ip
                g_ext_ip.clear()
                g_ext_ip.labels(**self.label, ip=ip or "unknown").set(1)
            except Exception:
                pass
        except Exception as exc:
            self._err("status", exc)

    def _collect_hosts(self):
        try:
            hosts = self._hosts.get_hosts_info()
            total = len(hosts)
            active = sum(1 for h in hosts if h.get("status"))
            g_hosts_total.labels(**self.label).set(total)
            g_hosts_active.labels(**self.label).set(active)
        except Exception as exc:
            self._err("hosts", exc)

    def _collect_wlan(self):
        band_map = {1: "2.4GHz", 2: "5GHz", 3: "5GHz-2", 4: "guest"}
        for idx, band in band_map.items():
            try:
                wlan = FritzWLAN(fc=self._fc, service=idx)
                g_wlan_clients.labels(**self.label, band=band).set(wlan.host_number)
                g_wlan_enabled.labels(**self.label, band=band).set(1 if wlan.is_enabled else 0)
            except Exception:
                # Service idx may not exist on this model — silent skip
                pass
