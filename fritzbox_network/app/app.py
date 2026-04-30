#!/usr/bin/env python3
"""FritzBox Network Visualizer – Flask Backend (with Mesh topology)"""
import os
import time
import json
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from collections import deque, defaultdict
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


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _norm_mac(mac: str) -> str:
    """Normalize MAC to uppercase colon-separated: AA:BB:CC:DD:EE:FF"""
    return mac.upper().replace("-", ":").strip() if mac else ""


def _device_type(hostname: str, interface: str, mesh_role: str = "") -> str:
    hn = (hostname or "").lower()
    # mesh_role is authoritative – never rely on hostname for router/repeater
    if mesh_role == "master":
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


def _fetch_hostlist_xml(fc) -> dict:
    """
    Call X_AVM-DE_GetHostListPath and parse the returned XML.

    Returns: normalised_mac → {
        "ap_mac":  str   – MAC of associated AP (WiFi only, else ""),
        "port":    int   – FritzBox LAN port number (1-4, 0 = unknown),
        "speed":   int|None  – link speed in Mbit/s,
    }

    The ap_mac field tells us which Fritz mesh node a WiFi client is
    connected to.  Ethernet devices that share a port number with a
    switch node are physically behind that switch.
    """
    out: dict = {}
    try:
        r    = fc.call_action("Hosts1", "X_AVM-DE_GetHostListPath")
        path = r.get("NewX_AVM-DE_HostListPath", "")
        if not path:
            return out
        url = f"http://{FRITZ_HOST}:{FRITZ_PORT}{path}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            xml_bytes = resp.read()
        root_el = ET.fromstring(xml_bytes)
        for item in root_el.findall("Item"):
            mac = _norm_mac(item.findtext("MACAddress") or "")
            if not mac:
                continue
            ap_mac  = _norm_mac(item.findtext("X_AVM-DE_AssociatedDeviceMAC") or "")
            port_s  = (item.findtext("X_AVM-DE_Port") or "0").strip()
            speed_s = (item.findtext("X_AVM-DE_Speed") or "").strip()
            freq_s   = (item.findtext("X_AVM-DE_Frequency") or "").strip()
            sig_s    = (item.findtext("X_AVM-DE_SignalStrength") or "").strip()
            out[mac] = {
                "ap_mac":    ap_mac,
                "port":      int(port_s) if port_s.isdigit() else 0,
                "speed":     int(speed_s) if speed_s.isdigit() else None,
                "signal":    int(sig_s)  if sig_s.isdigit()  else None,
                "frequency": int(freq_s) if freq_s.isdigit() else None,
            }
    except Exception as exc:
        log.warning("HostList-XML nicht verfügbar: %s", exc)
    return out


def _kbits_to_mbit(val) -> int | None:
    """Convert kbit/s (as returned by mesh JSON) to Mbit/s."""
    if val is None:
        return None
    v = int(val)
    return round(v / 1000) if v > 0 else None


def _build_mesh_links(mesh_json: dict | None, mac_to_id: dict) -> tuple[list, bool]:
    """
    Parse AVM mesh topology JSON and return (mesh_links, has_mesh).

    The mesh JSON stores each link under node_interfaces[].node_links[] with:
      node_1_uid  → parent mesh-node uid  (e.g. "n-1")
      node_2_uid  → child  mesh-node uid  (e.g. "n-75")
    Speeds are in kbit/s → converted to Mbit/s.
    """
    if not mesh_json:
        return [], False

    nodes_raw = mesh_json.get("nodes", [])

    # ── Step 1: map mesh node_uid → graph node_id via device_mac_address ──
    nuid_to_gid: dict[str, str] = {}

    for node in nodes_raw:
        nuid = node.get("uid", "")
        role = node.get("mesh_role", "")
        mac  = _norm_mac(node.get("device_mac_address", ""))

        if role == "master":
            nuid_to_gid[nuid] = "fritzbox_root"
        elif mac and mac in mac_to_id:
            nuid_to_gid[nuid] = mac_to_id[mac]

    # ── Step 2: collect all unique links (dedupe by link uid "nl-*") ──────
    seen_link_uids: set[str] = set()
    raw_links: list[dict]    = []

    for node in nodes_raw:
        for iface in node.get("node_interfaces", []):
            for lnk in iface.get("node_links", []):
                luid = lnk.get("uid", "")
                if luid and luid not in seen_link_uids:
                    seen_link_uids.add(luid)
                    raw_links.append(lnk)

    # ── Step 3: BFS from master to determine real parent→child depth ─────
    # node_1_uid is NOT always the topological parent in AVM mesh JSON.
    # We do a breadth-first search from the master node to compute depth,
    # then orient each link so the shallower (closer-to-master) node is
    # the source (parent) and the deeper node is the target (child).
    adj: dict[str, set] = defaultdict(set)
    for lnk in raw_links:
        if lnk.get("state") == "CONNECTED":
            u, v = lnk.get("node_1_uid", ""), lnk.get("node_2_uid", "")
            if u and v:
                adj[u].add(v)
                adj[v].add(u)

    master_uid = next(
        (n.get("uid", "") for n in nodes_raw if n.get("mesh_role") == "master"), ""
    )
    depth: dict[str, int] = {}
    if master_uid:
        q: deque = deque([master_uid])
        depth[master_uid] = 0
        while q:
            cur = q.popleft()
            for nb in adj[cur]:
                if nb not in depth:
                    depth[nb] = depth[cur] + 1
                    q.append(nb)

    # ── Step 4: build graph links with correct parent→child orientation ───
    links:    list[dict] = []
    has_mesh: bool       = False

    for lnk in raw_links:
        if lnk.get("state") != "CONNECTED":
            continue

        u1, u2 = lnk.get("node_1_uid", ""), lnk.get("node_2_uid", "")
        gid1   = nuid_to_gid.get(u1)
        gid2   = nuid_to_gid.get(u2)

        if not gid1 or not gid2 or gid1 == gid2:
            continue

        # Orient: shallower node (lower depth) = parent (source)
        d1, d2 = depth.get(u1, 99), depth.get(u2, 99)
        if d1 <= d2:
            src_gid, tgt_gid = gid1, gid2
        else:
            src_gid, tgt_gid = gid2, gid1

        has_mesh = True
        links.append({
            "source":    src_gid,
            "target":    tgt_gid,
            "link_type": lnk.get("type", "LAN"),
            "speed_rx":  _kbits_to_mbit(lnk.get("cur_data_rate_rx") or lnk.get("max_data_rate_rx")),
            "speed_tx":  _kbits_to_mbit(lnk.get("cur_data_rate_tx") or lnk.get("max_data_rate_tx")),
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

    # ── Fetch mesh JSON + host-list XML (parallel context data) ───────────
    mesh_json    = _fetch_mesh_json(fc)
    hostlist_info = _fetch_hostlist_xml(fc)   # mac → {ap_mac, port, speed}

    master_mac  = ""
    master_name = "FRITZ!Box"
    if mesh_json:
        for mnode in mesh_json.get("nodes", []):
            if mnode.get("mesh_role") == "master":
                master_mac  = _norm_mac(mnode.get("device_mac_address", ""))
                master_name = (mnode.get("device_friendly_name")
                               or mnode.get("device_name")
                               or "FRITZ!Box")
                break

    # ── Build node list ────────────────────────────────────────────────────
    root = {
        "id": "fritzbox_root", "name": master_name, "ip": FRITZ_HOST,
        "mac": master_mac, "type": "router", "active": True,
        "interface": "Router", "speed": None, "address_source": "",
        "mesh_role": "master",
    }
    nodes: list[dict] = [root]
    # Pre-register master MAC so hosts loop skips it and mesh links work
    mac_to_id: dict[str, str] = {}
    if master_mac:
        mac_to_id[master_mac] = "fritzbox_root"

    for host in raw_hosts:
        mac = _norm_mac(host.get("mac") or "")
        ip  = host.get("ip") or ""
        if not mac and not ip:
            continue
        # Skip the master FritzBox itself (already represented as root node)
        if mac and mac == master_mac:
            continue
        # Also skip if IP matches FritzBox IP and no MAC conflict
        if ip == FRITZ_HOST and not mac:
            continue

        node_id   = "h_" + (mac.replace(":", "") if mac else ip.replace(".", "_"))
        interface = host.get("interface_type") or "Ethernet"
        name      = host.get("name") or ip or "Unbekannt"
        active    = bool(host.get("status", False))

        # Speed from host-list XML (faster than per-host TR-064 call)
        speed = hostlist_info.get(mac, {}).get("speed") if mac else None

        nodes.append({
            "id": node_id, "name": name, "ip": ip, "mac": mac,
            "type": _device_type(name, interface),
            "active": active, "interface": interface,
            "speed": speed, "address_source": host.get("address_source") or "",
            "mesh_role": "",
        })
        if mac:
            mac_to_id[mac] = node_id

    # ── Promote slave mesh nodes (repeaters) ──────────────────────────────
    # Do this BEFORE building flat_links so repeaters get the right parent.
    if mesh_json:
        for mnode in mesh_json.get("nodes", []):
            role = mnode.get("mesh_role", "")
            mac  = _norm_mac(mnode.get("device_mac_address", ""))

            if role == "master":
                continue  # already handled as fritzbox_root

            if role == "slave":
                gid = mac_to_id.get(mac)
                if gid:
                    # Found by MAC → promote to repeater
                    for gn in nodes:
                        if gn["id"] == gid:
                            gn["type"]      = "repeater"
                            gn["mesh_role"] = "slave"
                            break
                else:
                    # Try name-based matching:
                    # collect all name variants from the mesh node
                    slave_name_candidates: set[str] = set()
                    for key in ("device_friendly_name", "device_name"):
                        v = (mnode.get(key) or "").strip().lower()
                        if v:
                            slave_name_candidates.add(v)
                            slave_name_candidates.add(v.replace(".", "-"))
                            slave_name_candidates.add(v.replace("-", "."))

                    matched_gn = None
                    if slave_name_candidates:
                        for gn in nodes[1:]:
                            gn_name = gn["name"].lower()
                            gn_variants = {
                                gn_name,
                                gn_name.replace(".", "-"),
                                gn_name.replace("-", "."),
                            }
                            if slave_name_candidates & gn_variants:
                                matched_gn = gn
                                break

                    if matched_gn:
                        if mac:
                            mac_to_id[mac] = matched_gn["id"]
                            matched_gn["mac"] = mac  # fill in the real MAC
                        matched_gn["type"]      = "repeater"
                        matched_gn["mesh_role"] = "slave"
                    else:
                        # Repeater not in hosts list → add as new node
                        node_ip = ""
                        for ip_e in mnode.get("ip_addresses", []):
                            if ip_e.get("version") == "V4" and "MANAGEMENT" in ip_e.get("attributes", []):
                                node_ip = ip_e.get("value", "").split("/")[0]
                                break
                        rep_name = (mnode.get("device_friendly_name")
                                    or mnode.get("device_name") or "Repeater")
                        node_id  = ("m_" + mac.replace(":", "")) if mac else f"m_{mnode.get('uid','x')}"
                        nodes.append({
                            "id": node_id, "name": rep_name, "ip": node_ip, "mac": mac,
                            "type": "repeater", "active": True,
                            "interface": "LAN", "speed": None, "address_source": "",
                            "mesh_role": "slave",
                        })
                        if mac:
                            mac_to_id[mac] = node_id

    # ── Enrich nodes with signal / frequency / ap_name from hostlist ──────
    for n in nodes:
        mac = n.get("mac", "")
        info = hostlist_info.get(mac, {}) if mac else {}
        n["signal"]    = info.get("signal")     # 0-100 or None
        n["frequency"] = info.get("frequency")  # 2400 / 5000 / None
        ap_mac_val = info.get("ap_mac", "")
        if ap_mac_val and ap_mac_val in mac_to_id:
            ap_nid = mac_to_id[ap_mac_val]
            ap_node = next((x for x in nodes if x["id"] == ap_nid), None)
            n["ap_name"] = ap_node["name"] if ap_node else ""
        else:
            n["ap_name"] = ""

    # ── Smart flat links ───────────────────────────────────────────────────
    # Built AFTER slave promotion so repeaters are already identified.
    #
    # Priority for parent selection:
    #  1. WiFi client → ap_mac from host-list XML (= the AP/repeater it connected to)
    #  2. LAN client  → same FritzBox port as a known switch node
    #  3. LAN client  → if exactly one switch in the network, route through it
    #                   (FritzBox doesn't reliably report ports for switch-attached
    #                   devices; this heuristic groups them visually anyway)
    #  4. Fallback    → fritzbox_root (star topology)

    # Build port → switch_node_id map from switch nodes
    port_to_switch: dict[int, str] = {}
    switch_ids: list[str] = []
    for n in nodes:
        if n["type"] == "switch":
            switch_ids.append(n["id"])
            if n.get("mac"):
                info = hostlist_info.get(n["mac"], {})
                p    = info.get("port", 0)
                if p > 0:
                    port_to_switch[p] = n["id"]
    sole_switch_id = switch_ids[0] if len(switch_ids) == 1 else None

    flat_links: list[dict] = []
    for n in nodes[1:]:
        parent_id = "fritzbox_root"
        mac = n.get("mac", "")
        if mac:
            info   = hostlist_info.get(mac, {})
            ap_mac = info.get("ap_mac", "")
            port   = info.get("port", 0)
            if ap_mac and ap_mac in mac_to_id:
                # WiFi: connect to the AP/repeater it's associated with
                ap_id = mac_to_id[ap_mac]
                if ap_id != n["id"]:                      # avoid self-loop
                    parent_id = ap_id
            elif n["type"] == "lan":
                # Pure LAN device → try port-match first, else sole-switch fallback
                if port > 0 and port in port_to_switch and port_to_switch[port] != n["id"]:
                    parent_id = port_to_switch[port]
                elif sole_switch_id and sole_switch_id != n["id"]:
                    parent_id = sole_switch_id

        flat_links.append({
            "source":    parent_id,
            "target":    n["id"],
            "link_type": "flat",
            "speed_rx":  n.get("speed"),
            "speed_tx":  None,
        })

    # Make sure the switch itself is connected to fritzbox_root, never to itself
    # or to one of its own children — its own flat_link entry already does that
    # because n["type"] == "switch" doesn't match any of the if/elif branches.

    mesh_links, has_mesh = _build_mesh_links(mesh_json, mac_to_id)

    return {
        "nodes":      nodes,
        "links":      flat_links,   # star/smart topology
        "mesh_links": mesh_links,   # real mesh topology
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
    force = request.args.get("force", "").lower() in ("1", "true", "yes")
    return jsonify(get_network_data(force=force))


@app.route("/api/refresh", methods=["GET", "POST"])
def api_refresh():
    return jsonify(get_network_data(force=True))


@app.route("/api/vendor")
def api_vendor():
    """
    Server-side proxy for MAC vendor lookup.
    Needed because HA Ingress CSP blocks direct browser requests to
    external APIs. Flask fetches from api.macvendors.com on behalf of
    the client and returns { vendor: "..." }.
    """
    mac = request.args.get("mac", "").strip()
    if not mac:
        return jsonify({"vendor": ""})
    try:
        url = f"https://api.macvendors.com/{urllib.parse.quote(mac)}"
        req = urllib.request.Request(url, headers={"Accept": "text/plain"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            vendor = resp.read().decode().strip()
        return jsonify({"vendor": vendor})
    except Exception:
        return jsonify({"vendor": ""})


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
