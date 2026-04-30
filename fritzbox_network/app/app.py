#!/usr/bin/env python3
"""FritzBox Network Visualizer – Flask Backend (with Mesh topology)"""
import os
import time
import json
import logging
import urllib.request
from flask import Flask, jsonify, render_template

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


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _norm_mac(mac: str) -> str:
    """Normalize MAC to uppercase colon-separated: AA:BB:CC:DD:EE:FF"""
    return mac.upper().replace("-", ":").strip() if mac else ""


def _device_type(hostname: str, interface: str, mesh_role: str = "") -> str:
    hn = (hostname or "").lower()
    if mesh_role == "master" or "fritz" in hn:
        return "router"
    if mesh_role == "slave":
        return "repeater"
    if any(k in hn for k in ("switch", "sw-", " sw", "hub", "unifi", "netgear-sw", "gs3")):
        return "switch"
    if interface == "802.11":
        return "wlan"
    return "lan"


# ─── Mesh topology ────────────────────────────────────────────────────────────

def _fetch_mesh_json(fc) -> dict | None:
    """
    Call X_AVM-DE_GetMeshListPath, then fetch the returned URL.
    The URL already contains a session-ID for auth.
    """
    try:
        result = fc.call_action("Hosts1", "X_AVM-DE_GetMeshListPath")
        path   = result.get("NewX_AVM-DE_MeshListPath", "")
        if not path:
            return None
        url = f"http://{FRITZ_HOST}:{FRITZ_PORT}{path}"
        with urllib.request.urlopen(url, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        log.warning("Mesh-JSON nicht verfügbar: %s", exc)
        return None


def _build_mesh_links(mesh_json: dict | None, mac_to_id: dict) -> tuple[list, bool]:
    """
    Parse mesh topology JSON and return (mesh_links, has_mesh).

    mesh_links: list of dicts with source/target (graph node IDs),
                link_type, speed_rx, speed_tx
    has_mesh:   True when real topology links were produced
    """
    if not mesh_json:
        return [], False

    nodes_raw = mesh_json.get("nodes", [])

    # ── Step 1: build interface_uid → {node_uid, mac} map ─────────────────
    iface_map: dict[str, dict] = {}   # iface_uid → {node_uid, mac}

    for node in nodes_raw:
        nuid = node.get("uid", "")
        for iface in node.get("node_interfaces", []):
            iuid = iface.get("uid", "")
            mac  = _norm_mac(iface.get("mac_address", ""))
            if iuid:
                iface_map[iuid] = {"node_uid": nuid, "mac": mac}

    # ── Step 2: map mesh node_uid → graph node_id ─────────────────────────
    nuid_to_gid: dict[str, str] = {}

    for node in nodes_raw:
        nuid = node.get("uid", "")
        role = node.get("mesh_role", "")

        if role == "master":
            nuid_to_gid[nuid] = "fritzbox_root"
            continue

        # Match via any interface MAC
        for iface in node.get("node_interfaces", []):
            mac = _norm_mac(iface.get("mac_address", ""))
            if mac and mac in mac_to_id:
                nuid_to_gid[nuid] = mac_to_id[mac]
                break

    # ── Step 3: iterate node_links and produce graph links ────────────────
    links: list[dict] = []
    seen:  set[tuple] = set()
    has_mesh = False

    for node in nodes_raw:
        src_nuid = node.get("uid", "")
        src_gid  = nuid_to_gid.get(src_nuid)

        for iface in node.get("node_interfaces", []):
            for lnk in iface.get("node_links", []):
                if lnk.get("state", "CONNECTED") != "CONNECTED":
                    continue

                tgt_iuid = lnk.get("node_interface_uid", "")
                tgt_info = iface_map.get(tgt_iuid, {})
                tgt_gid  = nuid_to_gid.get(tgt_info.get("node_uid", ""))

                if not src_gid or not tgt_gid or src_gid == tgt_gid:
                    continue

                key = tuple(sorted([src_gid, tgt_gid]))
                if key in seen:
                    continue
                seen.add(key)
                has_mesh = True

                speed_rx = lnk.get("cur_data_rate_rx") or lnk.get("max_data_rate_rx")
                speed_tx = lnk.get("cur_data_rate_tx") or lnk.get("max_data_rate_tx")

                links.append({
                    "source":    src_gid,
                    "target":    tgt_gid,
                    "link_type": lnk.get("type", "LAN"),
                    "speed_rx":  speed_rx,
                    "speed_tx":  speed_tx,
                })

    return links, has_mesh


# ─── Main data fetch ──────────────────────────────────────────────────────────

def _fetch_fresh() -> dict:
    try:
        from fritzconnection.core.fritzconnection import FritzConnection
        from fritzconnection.lib.fritzhosts import FritzHosts
    except ImportError:
        return {"error": "fritzconnection nicht installiert", "nodes": [], "links": [],
                "mesh_links": [], "has_mesh": False}

    try:
        fc = FritzConnection(
            address=FRITZ_HOST, port=FRITZ_PORT,
            user=FRITZ_USER, password=FRITZ_PASS, timeout=10,
        )
        fh = FritzHosts(fc=fc)
        raw_hosts = fh.get_hosts_info()
    except Exception as exc:
        log.error("FritzBox Verbindung fehlgeschlagen: %s", exc)
        return {"error": str(exc), "nodes": [], "links": [],
                "mesh_links": [], "has_mesh": False}

    # ── Build node list ────────────────────────────────────────────────────
    root = {
        "id": "fritzbox_root", "name": "FRITZ!Box", "ip": FRITZ_HOST,
        "mac": "", "type": "router", "active": True,
        "interface": "Router", "speed": None, "address_source": "",
        "mesh_role": "master",
    }
    nodes: list[dict] = [root]
    mac_to_id: dict[str, str] = {}   # normalized MAC → graph node_id

    for host in raw_hosts:
        mac = _norm_mac(host.get("mac") or "")
        ip  = host.get("ip") or ""
        if not mac and not ip:
            continue

        node_id   = "h_" + (mac.replace(":", "") if mac else ip.replace(".", "_"))
        interface = host.get("interface_type") or "Ethernet"
        name      = host.get("name") or ip or "Unbekannt"
        active    = bool(host.get("status", False))

        # Try to read per-host link speed
        speed = None
        if mac:
            try:
                res   = fc.call_action("Hosts1", "GetSpecificHostEntry", NewMACAddress=mac)
                raw_s = res.get("NewX_AVM-DE_Speed")
                if isinstance(raw_s, int) and 0 < raw_s < 100_000:
                    speed = raw_s
            except Exception:
                pass

        nodes.append({
            "id": node_id, "name": name, "ip": ip, "mac": mac,
            "type": _device_type(name, interface),
            "active": active, "interface": interface,
            "speed": speed, "address_source": host.get("address_source") or "",
            "mesh_role": "",
        })
        if mac:
            mac_to_id[mac] = node_id

    # ── Flat star links ────────────────────────────────────────────────────
    flat_links = [
        {"source": "fritzbox_root", "target": n["id"],
         "link_type": "flat", "speed_rx": n.get("speed"), "speed_tx": None}
        for n in nodes[1:]
    ]

    # ── Mesh topology links ────────────────────────────────────────────────
    mesh_json               = _fetch_mesh_json(fc)
    mesh_links, has_mesh    = _build_mesh_links(mesh_json, mac_to_id)

    # Nodes that appear in mesh → update their type from mesh_role
    if mesh_json:
        for mnode in mesh_json.get("nodes", []):
            role = mnode.get("mesh_role", "")
            if role not in ("master", "slave"):
                continue
            for iface in mnode.get("node_interfaces", []):
                mac = _norm_mac(iface.get("mac_address", ""))
                gid = mac_to_id.get(mac)
                if gid:
                    for gn in nodes:
                        if gn["id"] == gid:
                            gn["type"]      = _device_type(gn["name"], gn["interface"], role)
                            gn["mesh_role"] = role
                            break

    return {
        "nodes":      nodes,
        "links":      flat_links,   # star topology
        "mesh_links": mesh_links,   # real topology
        "has_mesh":   has_mesh,
    }


def get_network_data(force: bool = False) -> dict:
    global _cache
    now = time.time()
    if not force and _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]
    data = _fetch_fresh()
    if not data.get("error"):
        _cache = {"data": data, "ts": now}
    return data


# ─── Routes ───────────────────────────────────────────────────────────────────

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
    hosts = [n for n in data["nodes"] if n["type"] not in ("router", "repeater")]
    return jsonify({
        "ok": True, "has_mesh": data.get("has_mesh", False),
        "total": len(hosts),
        "active": sum(1 for h in hosts if h["active"]),
        "wlan":   sum(1 for h in hosts if h["type"] == "wlan"),
        "lan":    sum(1 for h in hosts if h["type"] in ("lan", "switch")),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False)
