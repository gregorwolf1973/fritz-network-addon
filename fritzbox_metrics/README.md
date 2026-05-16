# FritzBox & HA Metrics Exporter – Home Assistant Add-on

🇬🇧 English · [🇩🇪 Deutsch](README.de.md)

Pushes **FritzBox** (TR-064) and **Home Assistant** metrics to **InfluxDB 1.x**
every 15 seconds. Pair with the **InfluxDB** + **Grafana** community add-ons
for live, Netdata-style dashboards — fully self-hosted, no cloud, no Prometheus.

![Architectures](https://img.shields.io/badge/arch-aarch64%20|%20amd64%20|%20armv7-blue)
![Version](https://img.shields.io/badge/version-0.3.x-green)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

## Features

- **FritzBox metrics** via TR-064 — uptime, WAN state, downstream/upstream rate, DSL max, byte counters, external IP, total + active host count, WLAN clients per band (2.4 GHz / 5 GHz / Guest)
- **Home Assistant metrics** via Supervisor + Core API — HA Core CPU/RAM/network, host CPU/RAM, disk usage, entity counts per domain & per state, addon count
- **InfluxDB 1.x push** — works out of the box with the official `hassio-addons/addon-influxdb` (InfluxDB 1.7 + Chronograf)
- **Ready-made Grafana dashboard** included — 17 panels in 5 rows, one-click import
- **Configurable scrape interval** (default 15 s)
- **Selective sources** — disable FritzBox or HA collector individually
- **Auto-creates** the InfluxDB database on first run (if user has permission)
- **Multi-arch** — aarch64 (Raspberry Pi 4/5), amd64, armv7

## Installation

### Method 1: GitHub Repository (recommended)

[![Add to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fgregorwolf1973%2Ffritz-network-addon)

Click the button → repository is automatically added → continue with step 4.

Or manually:
1. In Home Assistant: **Settings → Add-ons → Add-on Store**
2. Top right **⋮ → Repositories**
3. Enter URL: `https://github.com/gregorwolf1973/fritz-network-addon`
4. **FritzBox & HA Metrics Exporter** appears in the store → **Install**
5. Configure (see below) → **Start**

### Method 2: Local add-on

1. Copy the `fritzbox_metrics/` folder to `/addons/` via SSH or Samba
2. **Settings → Add-ons → Add-on Store → ⋮ → Reload local add-ons**
3. **FritzBox & HA Metrics Exporter** under "Local add-ons" → **Install** → **Start**

## Quick Start

### 1. Install the InfluxDB community add-on

Add `https://github.com/hassio-addons/repository` as a repository, then install **InfluxDB** → **Start** → **Open Web UI**.

### 2. Create database + user in Chronograf

1. Left sidebar → **InfluxDB Admin** (gear-with-database icon)
2. Tab **Databases → + Create Database** → name: `metrics`
3. Tab **Users → + Create User** → username: `fritzbox_metrics`, password: pick one
4. Click the user → **Permissions** → grant **READ + WRITE** on `metrics`

### 3. Configure this add-on

```yaml
fritzbox_host: 192.168.178.1
fritzbox_port: 49000
fritzbox_user: "ha-metrics"          # FritzBox user with "Home Network" permission
fritzbox_password: "************"
influxdb_host: a0d7b954-influxdb     # InfluxDB community-addon internal hostname
influxdb_port: 8086
influxdb_database: metrics
influxdb_username: fritzbox_metrics
influxdb_password: "************"
scrape_interval: 15
enable_fritzbox: true
enable_homeassistant: true
log_level: info
```

Start → logs should show `Wrote N points to InfluxDB` every 15 seconds.

### 4. Install Grafana + import the dashboard

1. Install **Grafana** community add-on → **Open Web UI**
2. **Connections → Data sources → Add → InfluxDB**:
   - Query Language: **InfluxQL** _(important — not Flux!)_
   - URL: `http://a0d7b954-influxdb:8086`
   - Database: `metrics`
   - User / Password: as above
   - HTTP Method: `GET`
   - **Save & test**
3. **Dashboards → New → Import** → upload [`grafana/dashboard.json`](grafana/dashboard.json) → pick the InfluxDB datasource → **Import**

## Configuration reference

| Option | Default | Description |
|---|---|---|
| `fritzbox_host` | `192.168.178.1` | FritzBox IP |
| `fritzbox_port` | `49000` | TR-064 port |
| `fritzbox_user` | _empty_ | FritzBox user with **Home Network** permission |
| `fritzbox_password` | _empty_ | FritzBox user password |
| `influxdb_host` | `a0d7b954-influxdb` | InfluxDB hostname (community-addon internal) |
| `influxdb_port` | `8086` | InfluxDB port |
| `influxdb_database` | `metrics` | Target database |
| `influxdb_username` | _empty_ | InfluxDB user with R/W on the database |
| `influxdb_password` | _empty_ | InfluxDB user password |
| `scrape_interval` | `15` | Seconds between collects (5–3600) |
| `enable_fritzbox` | `true` | Enable FritzBox collector |
| `enable_homeassistant` | `true` | Enable Home Assistant collector |
| `log_level` | `info` | `debug` · `info` · `warning` · `error` |

## Measurements written

| Measurement | Fields | Tags |
|---|---|---|
| `fritzbox_wan` | uptime_seconds, connected, link_up, downstream_max_bps, upstream_max_bps, downstream_current_bps, upstream_current_bps, bytes_sent_total, bytes_received_total, external_ip | host |
| `fritzbox_hosts` | total, active | host |
| `fritzbox_wlan` | clients, enabled | host, band |
| `ha_core` | running, cpu_percent, memory_percent, memory_bytes, network_rx, network_tx | version |
| `ha_host` | cpu_percent, memory_used_bytes, memory_total_bytes, disk_total_gb, disk_used_gb, disk_free_gb | — |
| `ha_entities` | total | — |
| `ha_entities_by_domain` | count | domain |
| `ha_entities_by_state` | count | state |
| `ha_addons` | total, running | — |

## Troubleshooting

**`InfluxDB write failed: 401 Unauthorized`**
The InfluxDB user/password are wrong or the user lacks WRITE permission on the database. Re-check the Chronograf permission step.

**`Could not list/create database: 403`**
The user has no admin rights. Either create the database manually in Chronograf, or grant the user admin temporarily.

**`FritzBox connect failed: 401`**
Wrong FritzBox credentials. The user needs the **Home Network** permission. Anonymous TR-064 is enabled on some models — leaving user/password empty may work.

**Logs only show FritzBox lines, no HA**
Check that `enable_homeassistant: true` and `hassio_role: manager` is set (default). The `SUPERVISOR_TOKEN` is auto-injected — no manual setup needed.

**Grafana panels show "No data"**
- Verify the InfluxDB datasource uses **InfluxQL**, not Flux
- Check that the `metrics` database actually has data: in Chronograf, **Explore** → query `SHOW MEASUREMENTS ON metrics`

## Documentation

See [DOCS.md](DOCS.md) for the in-depth setup reference shown inside Home Assistant.

## Support

If this add-on saves you time, consider buying me a coffee:

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

## License

MIT
