#!/usr/bin/with-contenv bashio

set -e

bashio::log.info "Starting FritzBox & HA Metrics Exporter..."

export FRITZBOX_HOST=$(bashio::config 'fritzbox_host')
export FRITZBOX_PORT=$(bashio::config 'fritzbox_port')
export FRITZBOX_USER=$(bashio::config 'fritzbox_user')
export FRITZBOX_PASSWORD=$(bashio::config 'fritzbox_password')
export METRICS_PORT=$(bashio::config 'metrics_port')
export SCRAPE_INTERVAL=$(bashio::config 'scrape_interval')
export ENABLE_FRITZBOX=$(bashio::config 'enable_fritzbox')
export ENABLE_HOMEASSISTANT=$(bashio::config 'enable_homeassistant')
export LOG_LEVEL=$(bashio::config 'log_level')

# SUPERVISOR_TOKEN is auto-injected by the HA Supervisor when hassio_api: true
bashio::log.info "Metrics on :${METRICS_PORT}/metrics  (interval ${SCRAPE_INTERVAL}s)"

cd /app
exec python3 main.py
