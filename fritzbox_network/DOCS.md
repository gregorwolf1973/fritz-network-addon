# FritzBox Network Visualizer

Visualize every device on your FritzBox home network as an interactive
force-directed graph.

## Configuration

| Option              | Description                                              | Default           |
|---------------------|----------------------------------------------------------|-------------------|
| `fritzbox_host`     | IP address of your FritzBox                              | `192.168.178.1`   |
| `fritzbox_port`     | TR-064 port                                              | `49000`           |
| `fritzbox_user`     | FritzBox username (empty = anonymous, works on some models) | _empty_        |
| `fritzbox_password` | FritzBox password                                        | _empty_           |
| `web_port`          | Internal web server port (only exposed via Ingress)      | `8300`            |
| `cache_ttl`         | Seconds before the topology is re-fetched from FritzBox  | `30`              |

## FritzBox setup

1. Open the FritzBox UI → **System → FRITZ!Box users**
2. Create (or reuse) a user with **Home Network** permission
3. Enter the credentials in the add-on configuration

If TR-064 from the local network is allowed without authentication on
your model, you can leave user and password empty.

## Node legend

- **Red (F)** – Router / FritzBox master
- **Purple (R)** – Repeater / mesh slave
- **Blue (S / L)** – Switch / wired LAN device
- **Orange (W)** – Wi-Fi device

## Display toggles

- **Show names** – device hostnames under each node
- **Show IPs** – IP address under each node
- **Show inactive** – include offline devices
- **Show speed** – link speed label on each connection
- **Show Wi-Fi connections** – hide all links to Wi-Fi clients for a
  cleaner wired-only view

## Topology and layout

- **Flat topology** – every device on one hop from its parent (router,
  switch or AP). The add-on uses the FritzBox mesh JSON first, then
  falls back to port-matching for switch-attached LAN devices.
- **Mesh topology** – exact AVM mesh view (good for diagnosing repeater
  uplinks and channel allocations).
- **Force layout** – physics-based spring layout, free to rearrange.
- **Tree layout** – top-down hierarchy with the router on top.

## Interaction

- **Click** a node → detail modal with IP, MAC, vendor, signal, speed,
  band, AP attachment
- **Drag** a node → it stays pinned where you drop it; the position is
  saved in the browser
- **Double-click** a node → unpin and let it float again
- **Save layout** → persist all current positions
- **Reset layout** → clear all pinned positions and re-flow the graph
