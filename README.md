# FritzBox Network Visualizer – Home Assistant Addon

Zeigt alle Netzwerkteilnehmer deiner FritzBox als interaktiven Kraft-Graphen direkt in Home Assistant.

## Features

- **Interaktiver Netzwerkgraph** mit D3.js Force-Simulation
- **Farbkodierung**: Rot = Router/FritzBox · Blau = LAN/Switch · Orange = WLAN
- Namen und IP-Adressen per Toggle ein-/ausblenden
- Inaktive Geräte ausblenden
- Klick auf Gerät → Detailansicht mit Verbindungsgeschwindigkeit, IP, MAC
- IP anklicken → Web-Oberfläche des Geräts öffnen
- Hostname anklicken → SMB-Freigabe öffnen
- Zoom, Pan und Drag im Graphen
- Helles und dunkles Design
- Automatisches Caching (konfigurierbar)

## Installation

1. Home Assistant → **Einstellungen** → **Add-ons** → **Add-on Store**
2. Oben rechts auf die drei Punkte → **Repositories**
3. URL hinzufügen: `https://github.com/gregorwolf1973/fritz-network-addon`
4. Addon **FritzBox Network** installieren und konfigurieren

## Konfiguration

```yaml
fritzbox_host: "192.168.178.1"
fritzbox_port: 49000
fritzbox_user: ""
fritzbox_password: "dein-passwort"
web_port: 8300
cache_ttl: 30
```

## FritzBox einrichten

Unter **System → FRITZ!Box-Benutzer** einen Benutzer mit Berechtigung **Heimnetz** anlegen
und die Zugangsdaten in der Addon-Konfiguration eintragen.

## Screenshot

```
[Sidebar]          [Force-Graph]
Namen ✓            ●──(F)──●
IPs   ○                    |
                   ●───────●
Legende:
● Router
● LAN
● WLAN
```

## Lizenz

MIT
