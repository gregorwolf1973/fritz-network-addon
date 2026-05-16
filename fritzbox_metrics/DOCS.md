# FritzBox & HA Metrics Exporter

Collects metrics from **FritzBox** (TR-064) and **Home Assistant** (Supervisor + Core API), then **pushes them to InfluxDB 2.x** every N seconds. Pair with the **InfluxDB** and **Grafana** community add-ons for Netdata-style dashboards.

## Setup steps

### 1. Install the **InfluxDB** community add-on
From `https://github.com/hassio-addons/repository` — install, start, open its UI.

### 2. Create a token + bucket in InfluxDB
- **Data → Buckets → Create Bucket** → name e.g. `metrics`
- **API Tokens → Generate API Token → Custom API Token**
  - Read+Write permission on bucket `metrics`
- Copy the token (you only see it once)

### 3. Configure this add-on

| Option | Default | Description |
|---|---|---|
| `fritzbox_host` | `192.168.178.1` | FritzBox IP |
| `fritzbox_port` | `49000` | TR-064 port |
| `fritzbox_user` / `fritzbox_password` | _empty_ | FritzBox user with **Home Network** permission |
| `influxdb_url` | `http://a0d7b954-influxdb:8086` | InfluxDB community-addon internal hostname |
| `influxdb_token` | _empty_ | **paste the token here** |
| `influxdb_org` | `homeassistant` | InfluxDB org name |
| `influxdb_bucket` | `metrics` | bucket name |
| `scrape_interval` | `15` | seconds between collects |
| `enable_fritzbox` / `enable_homeassistant` | `true` | toggle sources |
| `log_level` | `info` | `debug`, `info`, `warning`, `error` |

### 4. Install **Grafana** community add-on
Add InfluxDB as a Flux datasource:
- URL: `http://a0d7b954-influxdb:8086`
- Token, org, default bucket as above

### 5. Build dashboards
Query examples (Flux):

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "fritzbox_wan")
  |> filter(fn: (r) => r._field == "downstream_current_bps")
```

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
