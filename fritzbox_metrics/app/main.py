#!/usr/bin/env python3
"""Collects metrics from FritzBox + Home Assistant and writes to InfluxDB 1.x."""
import logging
import os
import signal
import sys
import time

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError

from fritzbox import FritzCollector
from homeassistant import HACollector

LOG_LEVEL = os.environ.get("LOG_LEVEL", "info").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
log = logging.getLogger("exporter")

HOST = os.environ.get("INFLUXDB_HOST", "a0d7b954-influxdb")
PORT = int(os.environ.get("INFLUXDB_PORT", "8086"))
DB = os.environ.get("INFLUXDB_DATABASE", "metrics")
USER = os.environ.get("INFLUXDB_USERNAME", "") or None
PASS = os.environ.get("INFLUXDB_PASSWORD", "") or None

INTERVAL = int(os.environ.get("SCRAPE_INTERVAL", "15"))
ENABLE_FRITZ = os.environ.get("ENABLE_FRITZBOX", "true").lower() == "true"
ENABLE_HA = os.environ.get("ENABLE_HOMEASSISTANT", "true").lower() == "true"


def _ensure_database(client: InfluxDBClient):
    try:
        dbs = {d["name"] for d in client.get_list_database()}
        if DB not in dbs:
            log.info("Creating database '%s'", DB)
            client.create_database(DB)
        client.switch_database(DB)
    except InfluxDBClientError as exc:
        # Most likely insufficient privileges — log and continue, write may still work
        log.warning("Could not list/create database: %s", exc)
        client.switch_database(DB)


def run():
    log.info("Exporter starting — InfluxDB %s:%s db=%s interval=%ds",
             HOST, PORT, DB, INTERVAL)
    log.info("Sources — fritzbox=%s  homeassistant=%s", ENABLE_FRITZ, ENABLE_HA)

    client = InfluxDBClient(host=HOST, port=PORT, username=USER, password=PASS, timeout=10)
    _ensure_database(client)

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
                client.write_points(batch, database=DB)
                log.info("Wrote %d points to InfluxDB", len(batch))
            except Exception as exc:
                log.error("InfluxDB write failed: %s", exc)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    run()
