# FritzBox & HA Metrics Exporter – Home Assistant Add-on

[🇬🇧 English](README.md) · 🇩🇪 Deutsch

Schickt Metriken von **FritzBox** (TR-064) und **Home Assistant** alle 15 Sekunden
in **InfluxDB 1.x**. Zusammen mit den Community-Addons **InfluxDB** und
**Grafana** bekommst du Netdata-artige Live-Dashboards — komplett selbst gehostet,
ohne Cloud, ohne Prometheus.

![Architectures](https://img.shields.io/badge/arch-aarch64%20|%20amd64%20|%20armv7-blue)
![Version](https://img.shields.io/badge/version-0.3.x-green)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

## Funktionen

- **FritzBox-Metriken** über TR-064 — Uptime, WAN-Status, Down-/Upstream-Rate, DSL-Max, Byte-Zähler, externe IP, Hosts gesamt + aktiv, WLAN-Clients pro Band (2,4 GHz / 5 GHz / Gast)
- **Home-Assistant-Metriken** über Supervisor + Core API — HA-Core CPU/RAM/Netz, Host CPU/RAM, Disk-Auslastung, Entity-Zahlen pro Domain & pro Status, Addon-Anzahl
- **InfluxDB-1.x-Push** — funktioniert out-of-the-box mit dem offiziellen `hassio-addons/addon-influxdb` (InfluxDB 1.7 + Chronograf)
- **Fertiges Grafana-Dashboard** dabei — 17 Panels in 5 Reihen, ein Klick zum Importieren
- **Scrape-Intervall** konfigurierbar (Default: 15 s)
- **Quellen einzeln abschaltbar** — FritzBox oder HA-Collector deaktivieren
- **Database wird automatisch angelegt** beim ersten Start (sofern der User die Rechte hat)
- **Multi-Arch** — aarch64 (Raspberry Pi 4/5), amd64, armv7

## Installation

### Methode 1: GitHub-Repository (empfohlen)

[![Add to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fgregorwolf1973%2Ffritz-network-addon)

Auf den Button klicken → Repository wird automatisch hinzugefügt → weiter mit Schritt 4.

Oder manuell:
1. In Home Assistant: **Einstellungen → Add-ons → Add-on Store**
2. Oben rechts **⋮ → Repositories**
3. URL eintragen: `https://github.com/gregorwolf1973/fritz-network-addon`
4. **FritzBox & HA Metrics Exporter** erscheint im Store → **Installieren**
5. Konfigurieren (siehe unten) → **Starten**

### Methode 2: Lokales Addon

1. Den Ordner `fritzbox_metrics/` per SSH oder Samba nach `/addons/` kopieren
2. **Einstellungen → Add-ons → Add-on Store → ⋮ → Lokale Add-ons neu laden**
3. **FritzBox & HA Metrics Exporter** unter „Lokale Add-ons" → **Installieren** → **Starten**

## Schnellstart

### 1. InfluxDB-Community-Addon installieren

Repository `https://github.com/hassio-addons/repository` hinzufügen, dann **InfluxDB** installieren → **Starten** → **Web-UI öffnen**.

### 2. Database + User in Chronograf anlegen

1. Linke Seitenleiste → **InfluxDB Admin** (Zahnrad-mit-Datenbank-Symbol)
2. Tab **Databases → + Create Database** → Name: `metrics`
3. Tab **Users → + Create User** → Username: `fritzbox_metrics`, Passwort vergeben
4. Auf den User klicken → **Permissions** → **READ + WRITE** auf `metrics` setzen

### 3. Dieses Addon konfigurieren

```yaml
fritzbox_host: 192.168.178.1
fritzbox_port: 49000
fritzbox_user: "ha-metrics"          # FritzBox-User mit Recht "Heimnetz"
fritzbox_password: "************"
influxdb_host: a0d7b954-influxdb     # Interner Hostname des InfluxDB-Addons
influxdb_port: 8086
influxdb_database: metrics
influxdb_username: fritzbox_metrics
influxdb_password: "************"
scrape_interval: 15
enable_fritzbox: true
enable_homeassistant: true
log_level: info
```

Starten → das Log sollte alle 15 Sekunden `Wrote N points to InfluxDB` zeigen.

### 4. Grafana installieren + Dashboard importieren

1. **Grafana**-Community-Addon installieren → **Web-UI öffnen**
2. **Connections → Data sources → Add → InfluxDB**:
   - Query Language: **InfluxQL** _(wichtig — nicht Flux!)_
   - URL: `http://a0d7b954-influxdb:8086`
   - Database: `metrics`
   - User / Passwort: wie oben
   - HTTP Method: `GET`
   - **Save & test**
3. **Dashboards → New → Import** → [`grafana/dashboard.json`](grafana/dashboard.json) hochladen → InfluxDB-Datasource auswählen → **Import**

## Konfigurationsreferenz

| Option | Default | Beschreibung |
|---|---|---|
| `fritzbox_host` | `192.168.178.1` | IP der FritzBox |
| `fritzbox_port` | `49000` | TR-064-Port |
| `fritzbox_user` | _leer_ | FritzBox-User mit Recht **Heimnetz** |
| `fritzbox_password` | _leer_ | Passwort des FritzBox-Users |
| `influxdb_host` | `a0d7b954-influxdb` | InfluxDB-Hostname (Community-Addon intern) |
| `influxdb_port` | `8086` | InfluxDB-Port |
| `influxdb_database` | `metrics` | Ziel-Database |
| `influxdb_username` | _leer_ | InfluxDB-User mit R/W auf der Database |
| `influxdb_password` | _leer_ | InfluxDB-User-Passwort |
| `scrape_interval` | `15` | Sekunden zwischen den Abfragen (5–3600) |
| `enable_fritzbox` | `true` | FritzBox-Collector aktivieren |
| `enable_homeassistant` | `true` | Home-Assistant-Collector aktivieren |
| `log_level` | `info` | `debug` · `info` · `warning` · `error` |

## Geschriebene Measurements

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

## Fehlerbehebung

**`InfluxDB write failed: 401 Unauthorized`**
User/Passwort für InfluxDB stimmen nicht oder der User hat kein WRITE-Recht auf die Database. Schritt mit den Permissions in Chronograf nochmal prüfen.

**`Could not list/create database: 403`**
Der User hat keine Admin-Rechte. Entweder die Database in Chronograf manuell anlegen, oder den User vorübergehend zum Admin machen.

**`FritzBox connect failed: 401`**
FritzBox-Credentials falsch. Der User braucht das Recht **Heimnetz**. Manche Modelle erlauben TR-064 anonym im lokalen Netz — User/Passwort leer lassen funktioniert dann oft.

**Log zeigt nur FritzBox-Zeilen, kein HA**
Prüfen, dass `enable_homeassistant: true` gesetzt ist und `hassio_role: manager` (Default). Der `SUPERVISOR_TOKEN` wird automatisch injiziert — kein manuelles Setup nötig.

**Grafana-Panels zeigen „No data"**
- Sicherstellen, dass die InfluxDB-Datasource **InfluxQL** verwendet, nicht Flux
- In Chronograf prüfen ob in `metrics` Daten sind: **Explore** → `SHOW MEASUREMENTS ON metrics`

## Dokumentation

Siehe [DOCS.md](DOCS.md) für die ausführliche Setup-Referenz, die auch in Home Assistant angezeigt wird.

## Unterstützung

Wenn dir dieses Addon Zeit spart, freue ich mich über einen Kaffee:

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

## Lizenz

MIT
