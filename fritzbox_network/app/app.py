#!/usr/bin/env python3
"""FritzBox Network Visualizer – Flask Backend"""
import os
import time
import logging
from flask import Flask, jsonify, render_template, request

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fritznet")

app = Flask(__name__)

FRITZ_HOST = os.environ.get("FRITZBOX_HOST", "192.168.178.1")
FRITZ_PORT = int(os.environ.get("FRITZBOX_PORT", "49000"))
FRITZ_USER = os.environ.get("FRITZBOX_USER", "")
FRITZ_PASS = os.environ.get("FRITZBOX_PASSWORD", "")
CACHE_TTL  = int(os.environ.get("CACHE_TTL", "30"))
WEB_PORT   = int(os.environ.get("WEB_PORT", "8300"))

_cache: dict = {"data": None, "ts": 0.0}


def _device_type(hostname: str, interface: str) -> str:
    hn = (hostname or "").lower()
    if "fritz" in hn:
        return "router"
    if any(k in hn for k in ("switch", "sw-", " sw", "hub", "unifi", "netgear-sw")):
        return "switch"
    if interface == "802.11":
        return "wlan"
    return "lan"


def _fetch_fresh() -> dict:
    try:
        from fritzconnection.core.fritzconnection import FritzConnection
        from fritzconnection.lib.fritzhosts import FritzHosts
    except ImportError:
        return {"error": "fritzconnection nicht installiert", "nodes": [], "links": []}

    try:
        fc = FritzConnection(
            address=FRITZ_HOST,
            port=FRITZ_PORT,
            user=FRITZ_USER,
            password=FRITZ_PASS,
            timeout=10,
        )
        fh = FritzHosts(fc=fc)
        raw_hosts = fh.get_hosts_info()
    except Exception as exc:
        log.error("FritzBox Verbindung fehlgeschlagen: %s", exc)
        return {"error": str(exc), "nodes": [], "links": []}

    root = {
        "id": "fritzbox_root",
        "name": "FRITZ!Box",
        "ip": FRITZ_HOST,
        "mac": "",
        "type": "router",
        "active": True,
        "interface": "Router",
        "speed": None,
        "address_source": "",
    }
    nodes = [root]
    links = []

    for host in raw_hosts:
        mac = host.get("mac") or ""
        ip  = host.get("ip") or ""
        if not mac and not ip:
            continue

        node_id   = "h_" + (mac.replace(":", "") if mac else ip.replace(".", "_"))
        interface = host.get("interface_type") or "Ethernet"
        name      = host.get("name") or ip or "Unbekannt"
        active    = bool(host.get("status", False))

        speed = None
        if mac:
            try:
                res   = fc.call_action("Hosts1", "GetSpecificHostEntry", NewMACAddress=mac)
                speed = res.get("NewX_AVM-DE_Speed") or res.get("NewLeaseTimeRemaining")
                # Speed is in Mbit/s; filter out lease-time values
                if isinstance(speed, int) and speed > 100000:
                    speed = None
            except Exception:
                pass

        nodes.append({
            "id": node_id,
            "name": name,
            "ip": ip,
            "mac": mac,
            "type": _device_type(name, interface),
            "active": active,
            "interface": interface,
            "speed": speed,
            "address_source": host.get("address_source") or "",
        })
        links.append({"source": "fritzbox_root", "target": node_id})

    return {"nodes": nodes, "links": links}


def get_network_data(force: bool = False) -> dict:
    global _cache
    now = time.time()
    if not force and _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]
    data = _fetch_fresh()
    if not data.get("error"):
        _cache = {"data": data, "ts": now}
    return data


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/network")
def api_network():
    return jsonify(get_network_data())


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    return jsonify(get_network_data(force=True))


@app.route("/api/status")
def api_status():
    data = get_network_data()
    if data.get("error"):
        return jsonify({"ok": False, "error": data["error"]}), 503
    hosts = [n for n in data["nodes"] if n["type"] != "router"]
    return jsonify({
        "ok": True,
        "total": len(hosts),
        "active": sum(1 for h in hosts if h["active"]),
        "wlan": sum(1 for h in hosts if h["type"] == "wlan"),
        "lan": sum(1 for h in hosts if h["type"] in ("lan", "switch")),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False)
