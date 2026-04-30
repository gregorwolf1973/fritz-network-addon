# FritzBox Network Visualizer

Zeigt alle Netzwerkteilnehmer deiner FritzBox als interaktiven Kraft-Graphen.

## Konfiguration

| Option | Beschreibung | Standard |
|--------|-------------|---------|
| `fritzbox_host` | IP-Adresse der FritzBox | `192.168.178.1` |
| `fritzbox_port` | TR-064 Port | `49000` |
| `fritzbox_user` | FritzBox Benutzername (leer = kein Login) | `` |
| `fritzbox_password` | FritzBox Passwort | `` |
| `web_port` | Webserver Port | `8300` |
| `cache_ttl` | Cache-Dauer in Sekunden | `30` |

## FritzBox einrichten

1. FritzBox Benutzeroberfläche öffnen → **System** → **FRITZ!Box-Benutzer**
2. Benutzer mit Berechtigung **Heimnetz** anlegen (oder vorhandenen nutzen)
3. Unter **Heimnetz** → **Netzwerk** → **DNS-Rebind-Schutz** den TR-064 Zugriff prüfen
4. Alternativ: ohne Login mit leerem Benutzernamen (funktioniert bei manchen FritzBox-Modellen)

## Funktionen

- **Rot**: FritzBox / Router
- **Blau**: LAN-Geräte und Switches
- **Orange**: WLAN-Geräte
- Namen und IP-Adressen ein-/ausblenden
- Inaktive Geräte ausblenden
- Klick auf Gerät → Detailansicht mit IP-Link und SMB-Link
- Zoom und Pan im Graphen
- Helles / dunkles Design
