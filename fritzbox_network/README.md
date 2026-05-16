# FritzBox Network Visualizer – Home Assistant Add-on

![Architectures](https://img.shields.io/badge/arch-aarch64%20|%20amd64%20|%20armv7-blue)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

Visualize every device on your FritzBox home network as an interactive
force-directed graph — right inside Home Assistant. Router, repeaters,
switches, LAN clients and Wi-Fi clients are discovered automatically over
TR-064 and the FritzBox Mesh API, then rendered as a live, zoomable map.

![Topology preview](https://raw.githubusercontent.com/gregorwolf1973/fritz-network-addon/main/.github/preview.png)

## Features

- **Interactive force graph** (D3.js) — drag, zoom, pan, pin nodes
- **Two topology modes**: flat star or real AVM mesh
- **Two layout modes**: force simulation or top-down tree
- **Color-coded node types**: red = router · purple = repeater · blue = LAN/switch · orange = Wi-Fi
- **Smart parent detection** for LAN devices behind unmanaged switches
- **Mesh-to-mesh links** between FritzBox and repeaters with real speeds
- **Per-device detail modal**: IP, MAC, vendor lookup, signal strength, link speed, band (2.4/5 GHz), AP attachment
- **Toggles** for names, IPs, inactive devices, link speed labels and Wi-Fi connection lines
- **Layout persistence** — drag a node, it stays put across reloads
- **Settings persistence** — every toggle and mode survives a reload
- **Light & dark theme**
- **Server-side vendor proxy** so MAC lookups work behind the HA Ingress CSP

## Installation

[![Add to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fgregorwolf1973%2Ffritz-network-addon)

Click the button → repository is added to Home Assistant → install **FritzBox Network** from the Add-on Store → Start.

Or manually:
1. In Home Assistant: **Settings → Add-ons → Add-on Store**
2. Top right **⋮ → Repositories**
3. Enter URL: `https://github.com/gregorwolf1973/fritz-network-addon`
4. **FritzBox Network** appears in the store → Install → Start
5. Open the side panel **FritzBox Network**

## Configuration

```yaml
fritzbox_host: "192.168.178.1"  # IP of your FritzBox
fritzbox_port: 49000            # TR-064 port (default)
fritzbox_user: ""               # FritzBox user with "Home Network" permission
fritzbox_password: ""           # password
web_port: 8300                  # web UI port (only exposed via Ingress)
cache_ttl: 30                   # seconds before the topology is re-fetched
```

### Creating a FritzBox user

1. Open the FritzBox UI → **System → FRITZ!Box users**
2. Add a user with permission **Home Network** (or reuse an existing one)
3. Put the credentials into the add-on configuration

Leaving user/password empty works on some FritzBox models that allow anonymous TR-064 access on the local network.

## How the topology is built

The add-on combines three FritzBox data sources for the most accurate view:

1. **TR-064 host list** — every known device with IP, MAC, online state
2. **`X_AVM-DE_GetHostListPath` XML** — port number, Wi-Fi association (`AssociatedDeviceMAC`), link speed, signal, frequency band
3. **`X_AVM-DE_GetMeshListPath` JSON** — the FritzBox's own mesh view with repeater and switch links

For LAN devices, the AVM mesh sometimes drops the switch hop (a passive switch is L2-transparent). The add-on detects this and routes those clients through the matching switch via port number, so the diagram keeps matching reality across refreshes.

## Documentation

See [DOCS.md](DOCS.md) for the in-depth configuration reference shown inside Home Assistant.

## Support

If this add-on saves you time or makes your home network make sense, consider buying me a coffee:

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

## License

MIT
