#!/usr/bin/env sh
set -eu

echo "=== Bootstrapping API service ==="

vpn_flag="$(printf '%s' "${VPN_ENABLED:-0}" | tr '[:upper:]' '[:lower:]')"
if [ "$vpn_flag" = "1" ] || [ "$vpn_flag" = "true" ] || [ "$vpn_flag" = "yes" ] || [ "$vpn_flag" = "on" ]; then
    echo "Ensuring WireGuard/AWG interface before starting the app..."
    if ! python -m app.core.vpn_bootstrap; then
        echo "ERROR: VPN bootstrap failed! Application will not start without VPN." >&2
        exit 1
    fi
    echo "VPN interface is up and running."
fi

echo "Applying database migrations..."
# Use 'heads' to handle multiple head revisions (merge migrations)
if ! alembic upgrade heads; then
    echo "ERROR: Failed to apply database migrations!" >&2
    exit 1
fi
echo "Database migrations applied successfully."

echo "Creating default admin user..."
if ! python create_admin.py admin@test.com admin123; then
    echo "WARNING: Failed to create default admin user (may already exist)" >&2
fi

echo "Starting application..."
exec python main.py
