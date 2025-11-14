#!/usr/bin/env sh
set -eu

echo "=== Bootstrapping Celery worker ==="

# Initialize metric definitions if database is empty
echo "Checking metric definitions in database..."
python -c "
import asyncio
import sys
from app.db.session import AsyncSessionLocal
from app.repositories.metric import MetricDefRepository

async def check_metrics():
    async with AsyncSessionLocal() as db:
        repo = MetricDefRepository(db)
        metrics = await repo.list_all(active_only=False)
        print(f'Found {len(metrics)} metric definitions in database')
        if len(metrics) == 0:
            print('WARNING: No metric definitions found. Please run seed_metric_defs.py or wait for auto-seed on app startup.')

asyncio.run(check_metrics())
" || echo "WARNING: Failed to check metric definitions (database may not be ready yet)"

vpn_flag="$(printf '%s' "${VPN_ENABLED:-0}" | tr '[:upper:]' '[:lower:]')"
if [ "$vpn_flag" = "1" ] || [ "$vpn_flag" = "true" ] || [ "$vpn_flag" = "yes" ] || [ "$vpn_flag" = "on" ]; then
    echo "Ensuring WireGuard/AWG interface before starting the worker..."
    if ! python -m app.core.vpn_bootstrap; then
        echo "ERROR: VPN bootstrap failed! Worker will not start without VPN." >&2
        exit 1
    fi
    echo "VPN interface is up and running."
else
    echo "WARNING: VPN is disabled (VPN_ENABLED=0). Gemini API may not be accessible due to geographic restrictions."
    echo "If you see 'User location is not supported' errors, enable VPN by setting VPN_ENABLED=1"
fi

echo "Starting Celery worker for extraction queue..."
exec celery -A app.core.celery_app.celery_app worker -l info -Q extraction

