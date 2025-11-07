#!/usr/bin/env sh
set -eu

echo "=== Bootstrapping API service ==="

vpn_flag="$(printf '%s' "${VPN_ENABLED:-0}" | tr '[:upper:]' '[:lower:]')"
if [ "$vpn_flag" = "1" ] || [ "$vpn_flag" = "true" ] || [ "$vpn_flag" = "yes" ] || [ "$vpn_flag" = "on" ]; then
    echo "Ensuring WireGuard interface before starting the app..."
    python -m app.core.vpn_bootstrap
fi

echo "Applying database migrations..."
alembic upgrade head

echo "Starting application..."
exec python main.py
