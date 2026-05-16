# FritzBox & HA Metrics Exporter

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

Collects metrics from **FritzBox** (TR-064) and **Home Assistant**
(Supervisor + Core API) and **pushes them to InfluxDB 1.x** every N seconds.

> 📖 Full README with troubleshooting & screenshots: [English](README.md) · [Deutsch](README.de.md)

Designed for the official **InfluxDB** community add-on
(`hassio-addons/addon-influxdb`, ships **InfluxDB 1.7** with Chronograf
+ Kapacitor) — pair with the **Grafana** community add-on for
Netdata-style dashboards.

## Setup

### 1. Install the **InfluxDB** community add-on
Repository: `https://github.com/hassio-addons/repository` → install, start.

### 2. Open Chronograf and create a database + user

1. In the InfluxDB add-on click **OPEN WEB UI** → Chronograf opens
2. Left sidebar → **InfluxDB Admin** (gear-with-database icon)
3. Tab **Databases** → **+ Create Database** → name e.g. `metrics`
4. Tab **Users** → **+ Create User**:
   - username e.g. `fritzbox_metrics`
   - password (remember it)
5. Click the user → **Permissions** → grant **READ** + **WRITE** on the `metrics` database

### 3. Configure this add-on

| Option | Default | Description |
|---|---|---|
| `fritzbox_host` | `192.168.178.1` | FritzBox IP |
| `fritzbox_port` | `49000` | TR-064 port |
| `fritzbox_user` / `fritzbox_password` | _empty_ | FritzBox user with **Home Network** permission |
| `influxdb_host` | `a0d7b954-influxdb` | internal hostname of the InfluxDB add-on |
| `influxdb_port` | `8086` | |
| `influxdb_database` | `metrics` | database name (must match step 2) |
| `influxdb_username` | _empty_ | the user from step 2 |
| `influxdb_password` | _empty_ | the password from step 2 |
| `scrape_interval` | `15` | seconds between collects |
| `enable_fritzbox` / `enable_homeassistant` | `true` | toggle sources |
| `log_level` | `info` | `debug`, `info`, `warning`, `error` |

Start the add-on. Logs should show `Wrote N points to InfluxDB` every interval.

### 4. Install **Grafana** community add-on

Add **InfluxDB** as data source (InfluxQL flavor, NOT Flux for 1.x):
- URL: `http://a0d7b954-influxdb:8086`
- Database: `metrics`
- User / Password: as created above
- HTTP Method: `GET`

### 5. Import the ready-made dashboard

A starter dashboard lives at [`grafana/dashboard.json`](grafana/dashboard.json).

In Grafana: **Dashboards → New → Import → Upload JSON file** → pick `dashboard.json` → select your InfluxDB datasource → **Import**.

It includes panels for WAN throughput, WAN bytes counters, WLAN clients per band, host/active counts, HA Core CPU/RAM/network, host disk gauge, entities by domain & state, and addon counts.

## Measurements

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

## Sample Grafana queries (InfluxQL)

```sql
-- Current WAN downstream (live)
SELECT mean("downstream_current_bps") FROM "fritzbox_wan"
WHERE $timeFilter GROUP BY time(15s) fill(null)

-- WLAN clients per band
SELECT mean("clients") FROM "fritzbox_wlan"
WHERE $timeFilter GROUP BY time(1m), "band" fill(null)

-- HA Core CPU
SELECT mean("cpu_percent") FROM "ha_core"
WHERE $timeFilter GROUP BY time(15s) fill(null)
```
