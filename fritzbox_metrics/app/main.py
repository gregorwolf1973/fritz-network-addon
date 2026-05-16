#!/usr/bin/env python3
"""Prometheus exporter for FritzBox + Home Assistant.

Exposes metrics on :METRICS_PORT/metrics  (default 9709).
Add this as a scrape target in the HA Prometheus add-on:

  scrape_configs:
    - job_name: fritzbox_ha
      static_configs:
        - targets: ['<HA-IP>:9709']
"""
import logging
import os
import signal
import sys
import time

from prometheus_client import start_http_server, Gauge

from fritzbox import FritzCollector
from homeassistant import HACollector

LOG_LEVEL = os.environ.get("LOG_LEVEL", "info").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
log = logging.getLogger("exporter")

PORT = int(os.environ.get("METRICS_PORT", "9709"))
INTERVAL = int(os.environ.get("SCRAPE_INTERVAL", "15"))
ENABLE_FRITZ = os.environ.get("ENABLE_FRITZBOX", "true").lower() == "true"
ENABLE_HA = os.environ.get("ENABLE_HOMEASSISTANT", "true").lower() == "true"

g_last_scrape = Gauge("exporter_last_scrape_timestamp", "Unix ts of last scrape", ["source"])
g_scrape_duration = Gauge("exporter_scrape_duration_seconds", "Scrape duration", ["source"])


def run():
    log.info("Exporter starting on :%d (interval=%ds)", PORT, INTERVAL)
    log.info("Sources — fritzbox=%s  homeassistant=%s", ENABLE_FRITZ, ENABLE_HA)

    start_http_server(PORT)

    fritz = FritzCollector() if ENABLE_FRITZ else None
    ha = HACollector() if ENABLE_HA else None

    def _shutdown(*_):
        log.info("Shutting down.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    while True:
        if fritz:
            t0 = time.time()
            try:
                fritz.collect()
            except Exception as exc:
                log.exception("FritzBox collect failed: %s", exc)
            dur = time.time() - t0
            g_last_scrape.labels(source="fritzbox").set(time.time())
            g_scrape_duration.labels(source="fritzbox").set(dur)
            log.debug("FritzBox scrape done in %.2fs", dur)

        if ha:
            t0 = time.time()
            try:
                ha.collect()
            except Exception as exc:
                log.exception("HA collect failed: %s", exc)
            dur = time.time() - t0
            g_last_scrape.labels(source="homeassistant").set(time.time())
            g_scrape_duration.labels(source="homeassistant").set(dur)
            log.debug("HA scrape done in %.2fs", dur)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    run()
