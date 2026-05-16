#!/usr/bin/env python3
"""Collects metrics from FritzBox + Home Assistant and writes them to InfluxDB 2.x."""
import logging
import os
import signal
import sys
import time

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from fritzbox import FritzCollector
from homeassistant import HACollector

LOG_LEVEL = os.environ.get("LOG_LEVEL", "info").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
log = logging.getLogger("exporter")

INFLUX_URL = os.environ.get("INFLUXDB_URL", "http://a0d7b954-influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUXDB_TOKEN", "")
INFLUX_ORG = os.environ.get("INFLUXDB_ORG", "homeassistant")
INFLUX_BUCKET = os.environ.get("INFLUXDB_BUCKET", "metrics")

INTERVAL = int(os.environ.get("SCRAPE_INTERVAL", "15"))
ENABLE_FRITZ = os.environ.get("ENABLE_FRITZBOX", "true").lower() == "true"
ENABLE_HA = os.environ.get("ENABLE_HOMEASSISTANT", "true").lower() == "true"


def run():
    log.info("Exporter starting — interval=%ds  bucket=%s", INTERVAL, INFLUX_BUCKET)
    log.info("Sources — fritzbox=%s  homeassistant=%s", ENABLE_FRITZ, ENABLE_HA)

    if not INFLUX_TOKEN:
        log.error("INFLUXDB_TOKEN is empty — set it in the addon options")
        sys.exit(1)

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    fritz = FritzCollector() if ENABLE_FRITZ else None
    ha = HACollector() if ENABLE_HA else None

    def _shutdown(*_):
        log.info("Shutting down.")
        try:
            client.close()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    while True:
        batch = []
        for src, c in (("fritzbox", fritz), ("homeassistant", ha)):
            if not c:
                continue
            t0 = time.time()
            try:
                pts = c.collect()
                batch.extend(pts)
                log.debug("%s: %d points in %.2fs", src, len(pts), time.time() - t0)
            except Exception as exc:
                log.exception("%s collect failed: %s", src, exc)

        if batch:
            try:
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=batch)
                log.info("Wrote %d points to InfluxDB", len(batch))
            except Exception as exc:
                log.error("InfluxDB write failed: %s", exc)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    run()
