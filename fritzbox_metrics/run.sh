#!/usr/bin/with-contenv bashio

set -e

bashio::log.info "Starting FritzBox & HA Metrics Exporter (InfluxDB push)..."

export FRITZBOX_HOST=$(bashio::config 'fritzbox_host')
export FRITZBOX_PORT=$(bashio::config 'fritzbox_port')
export FRITZBOX_USER=$(bashio::config 'fritzbox_user')
export FRITZBOX_PASSWORD=$(bashio::config 'fritzbox_password')

export INFLUXDB_URL=$(bashio::config 'influxdb_url')
export INFLUXDB_TOKEN=$(bashio::config 'influxdb_token')
export INFLUXDB_ORG=$(bashio::config 'influxdb_org')
export INFLUXDB_BUCKET=$(bashio::config 'influxdb_bucket')

export SCRAPE_INTERVAL=$(bashio::config 'scrape_interval')
export ENABLE_FRITZBOX=$(bashio::config 'enable_fritzbox')
export ENABLE_HOMEASSISTANT=$(bashio::config 'enable_homeassistant')
export LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "InfluxDB: ${INFLUXDB_URL}  bucket=${INFLUXDB_BUCKET}  interval=${SCRAPE_INTERVAL}s"

cd /app
exec python3 main.py
