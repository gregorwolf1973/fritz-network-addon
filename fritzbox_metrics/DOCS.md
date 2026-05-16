# FritzBox & HA Metrics Exporter

Prometheus exporter for **FritzBox** (via TR-064) and **Home Assistant**
(via Supervisor + Core REST API). Point the official **Prometheus**
add-on at this exporter and visualize everything in **Grafana** —
Netdata-style live dashboards, but built from existing HA add-ons.

## Configuration

| Option | Default | Description |
|---|---|---|
| `fritzbox_host` | `192.168.178.1` | FritzBox IP |
| `fritzbox_port` | `49000` | TR-064 port |
| `fritzbox_user` | _empty_ | FritzBox user with **Home Network** permission |
| `fritzbox_password` | _empty_ | password |
| `metrics_port` | `9709` | port for `/metrics` endpoint |
| `scrape_interval` | `15` | seconds between collector runs |
| `enable_fritzbox` | `true` | enable FritzBox collector |
| `enable_homeassistant` | `true` | enable HA collector |
| `log_level` | `info` | `debug`, `info`, `warning`, `error` |

## Hooking up Prometheus

Install the official Prometheus add-on and add to its config:

```yaml
scrape_configs:
  - job_name: fritzbox_ha
    scrape_interval: 15s
    static_configs:
      - targets: ['homeassistant.local:9709']
```

(Replace `homeassistant.local` with your HA host IP if needed.)

## Exposed metrics

### FritzBox
- `fritzbox_uptime_seconds`
- `fritzbox_connected`, `fritzbox_link_up`
- `fritzbox_external_ip_info{ip=…}`
- `fritzbox_downstream_max_bps`, `fritzbox_upstream_max_bps`
- `fritzbox_downstream_current_bps`, `fritzbox_upstream_current_bps`
- `fritzbox_bytes_sent_total`, `fritzbox_bytes_received_total`
- `fritzbox_hosts_total`, `fritzbox_hosts_active`
- `fritzbox_wlan_clients{band=…}`, `fritzbox_wlan_enabled{band=…}`

### Home Assistant
- `ha_core_cpu_percent`, `ha_core_memory_percent`, `ha_core_memory_bytes`
- `ha_core_network_rx_bytes`, `ha_core_network_tx_bytes`
- `ha_core_running`, `ha_core_version_info{version=…}`
- `ha_host_cpu_percent`, `ha_host_memory_used_bytes`, `ha_host_memory_total_bytes`
- `ha_host_disk_used_bytes`, `ha_host_disk_total_bytes`, `ha_host_disk_free_bytes`
- `ha_entities_total{domain=…}`
- `ha_entity_state_total{state=…}`
- `ha_addons_total`, `ha_addons_running`

### Exporter self-metrics
- `exporter_last_scrape_timestamp{source=…}`
- `exporter_scrape_duration_seconds{source=…}`
- `fritzbox_collect_errors_total{source=…}`
- `ha_collect_errors_total{source=…}`
