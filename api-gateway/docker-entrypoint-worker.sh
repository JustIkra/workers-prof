#!/usr/bin/env sh
set -eu

echo "=== Bootstrapping Celery worker ==="

vpn_flag="$(printf '%s' "${VPN_ENABLED:-0}" | tr '[:upper:]' '[:lower:]')"
if [ "$vpn_flag" = "1" ] || [ "$vpn_flag" = "true" ] || [ "$vpn_flag" = "yes" ] || [ "$vpn_flag" = "on" ]; then
    echo "Ensuring WireGuard interface before starting the worker..."
    python -m app.core.vpn_bootstrap
fi

echo "Starting Celery worker for extraction queue..."
exec celery -A app.core.celery_app.celery_app worker -l info -Q extraction

