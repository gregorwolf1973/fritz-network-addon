#!/usr/bin/with-contenv bashio

set -e

bashio::log.info "Starting FritzBox & HA Metrics Exporter (InfluxDB 1.x push)..."

export FRITZBOX_HOST=$(bashio::config 'fritzbox_host')
export FRITZBOX_PORT=$(bashio::config 'fritzbox_port')
export FRITZBOX_USER=$(bashio::config 'fritzbox_user')
export FRITZBOX_PASSWORD=$(bashio::config 'fritzbox_password')

export INFLUXDB_HOST=$(bashio::config 'influxdb_host')
export INFLUXDB_PORT=$(bashio::config 'influxdb_port')
export INFLUXDB_DATABASE=$(bashio::config 'influxdb_database')
export INFLUXDB_USERNAME=$(bashio::config 'influxdb_username')
export INFLUXDB_PASSWORD=$(bashio::config 'influxdb_password')

export SCRAPE_INTERVAL=$(bashio::config 'scrape_interval')
export ENABLE_FRITZBOX=$(bashio::config 'enable_fritzbox')
export ENABLE_HOMEASSISTANT=$(bashio::config 'enable_homeassistant')
export LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "InfluxDB: ${INFLUXDB_HOST}:${INFLUXDB_PORT}/${INFLUXDB_DATABASE}  interval=${SCRAPE_INTERVAL}s"

cd /app
exec python3 main.py
