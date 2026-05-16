# FritzBox Home Assistant Add-on Repository

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

Two Home Assistant add-ons for FritzBox users:

## 🗺️ [FritzBox Network](./fritzbox_network)

Interactive **force-directed topology graph** of every device on your FritzBox home network — router, repeaters, switches, LAN clients and Wi-Fi clients, all auto-discovered via TR-064 and the FritzBox Mesh API.

![Topology preview](https://raw.githubusercontent.com/gregorwolf1973/fritz-network-addon/main/.github/preview.png)

📖 Docs: [`fritzbox_network/DOCS.md`](./fritzbox_network/DOCS.md)

## 📊 [FritzBox & HA Metrics Exporter](./fritzbox_metrics)

**InfluxDB exporter** for FritzBox (TR-064) and Home Assistant (Supervisor + Core API). Pair with the official **InfluxDB** and **Grafana** community add-ons for live, Netdata-style dashboards — no Prometheus, no cloud.

Ships with a **ready-made Grafana dashboard** (17 panels, one-click import).

📖 Docs: [English](./fritzbox_metrics/README.md) · [Deutsch](./fritzbox_metrics/README.de.md)

---

## Installation

[![Add to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fgregorwolf1973%2Ffritz-network-addon)

Click the button → repository is automatically added to Home Assistant → install either add-on from the Add-on Store → Start.

Or manually:
1. In Home Assistant: **Settings → Add-ons → Add-on Store**
2. Top right **⋮ → Repositories**
3. Enter this URL:
   ```
   https://github.com/gregorwolf1973/fritz-network-addon
   ```
4. The add-ons appear in the store → Install the ones you want → Start

## Support

If these add-ons save you time, consider buying me a coffee:

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/gregorwolf1973)

## License

MIT
