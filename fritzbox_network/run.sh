#!/usr/bin/with-contenv bashio

set -e

bashio::log.info "Starting FritzBox Network Visualizer..."

export FRITZBOX_HOST=$(bashio::config 'fritzbox_host')
export FRITZBOX_PORT=$(bashio::config 'fritzbox_port')
export FRITZBOX_USER=$(bashio::config 'fritzbox_user')
export FRITZBOX_PASSWORD=$(bashio::config 'fritzbox_password')
export WEB_PORT=$(bashio::config 'web_port')
export CACHE_TTL=$(bashio::config 'cache_ttl')

bashio::log.info "Connecting to FritzBox at ${FRITZBOX_HOST}:${FRITZBOX_PORT}"

cd /app
exec python3 app.py
