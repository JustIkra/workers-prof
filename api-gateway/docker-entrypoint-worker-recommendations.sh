#!/usr/bin/env sh
set -eu

# shellcheck shell=sh

echo "=== Bootstrapping Celery worker for recommendations ==="

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

ai_flag="$(printf '%s' "${AI_RECOMMENDATIONS_ENABLED:-1}" | tr '[:upper:]' '[:lower:]')"
if [ "$ai_flag" = "0" ] || [ "$ai_flag" = "false" ] || [ "$ai_flag" = "no" ] || [ "$ai_flag" = "off" ]; then
    echo "WARNING: AI recommendations are disabled (AI_RECOMMENDATIONS_ENABLED=${AI_RECOMMENDATIONS_ENABLED:-0})."
    echo "Tasks in the recommendations queue will mark results as 'disabled'."
else
    gemini_key_count="$(python - <<'PY'
import os
keys = [k.strip() for k in os.environ.get("GEMINI_API_KEYS", "").split(",") if k.strip()]
print(len(keys))
PY
)"
    if [ "$gemini_key_count" = "0" ]; then
        echo "ERROR: GEMINI_API_KEYS is not configured but AI recommendations are enabled." >&2
        echo "Set GEMINI_API_KEYS or disable recommendations via AI_RECOMMENDATIONS_ENABLED=0." >&2
        exit 1
    else
        echo "Detected ${gemini_key_count} Gemini API key(s) configured for recommendations."
    fi
fi

queues="${CELERY_WORKER_QUEUES:-recommendations}"
log_level="${CELERY_LOG_LEVEL:-info}"

set -- celery -A app.core.celery_app.celery_app worker -l "$log_level" -Q "$queues"

if [ -n "${CELERY_WORKER_CONCURRENCY:-}" ]; then
    echo "Setting Celery concurrency to ${CELERY_WORKER_CONCURRENCY}."
    set -- "$@" -c "${CELERY_WORKER_CONCURRENCY}"
fi

if [ -n "${CELERY_WORKER_HOSTNAME:-}" ]; then
    echo "Using Celery worker hostname ${CELERY_WORKER_HOSTNAME}."
    set -- "$@" -n "${CELERY_WORKER_HOSTNAME}"
fi

if [ -n "${CELERY_WORKER_STATE_DB:-}" ]; then
    echo "Persisting worker state to ${CELERY_WORKER_STATE_DB}."
    set -- "$@" --statedb "${CELERY_WORKER_STATE_DB}"
fi

if [ -n "${CELERY_WORKER_PIDFILE:-}" ]; then
    echo "Writing worker PID file to ${CELERY_WORKER_PIDFILE}."
    set -- "$@" --pidfile "${CELERY_WORKER_PIDFILE}"
fi

if [ -n "${CELERY_WORKER_MAX_TASKS_PER_CHILD:-}" ]; then
    echo "Configuring max tasks per child: ${CELERY_WORKER_MAX_TASKS_PER_CHILD}."
    set -- "$@" --max-tasks-per-child "${CELERY_WORKER_MAX_TASKS_PER_CHILD}"
fi

if [ -n "${CELERY_WORKER_PREFETCH_MULTIPLIER:-}" ]; then
    echo "Configuring prefetch multiplier: ${CELERY_WORKER_PREFETCH_MULTIPLIER}."
    set -- "$@" --prefetch-multiplier "${CELERY_WORKER_PREFETCH_MULTIPLIER}"
fi

if [ -n "${CELERY_WORKER_TIME_LIMIT:-}" ]; then
    echo "Configuring hard time limit: ${CELERY_WORKER_TIME_LIMIT} seconds."
    set -- "$@" --time-limit "${CELERY_WORKER_TIME_LIMIT}"
fi

if [ -n "${CELERY_WORKER_SOFT_TIME_LIMIT:-}" ]; then
    echo "Configuring soft time limit: ${CELERY_WORKER_SOFT_TIME_LIMIT} seconds."
    set -- "$@" --soft-time-limit "${CELERY_WORKER_SOFT_TIME_LIMIT}"
fi

if [ -n "${CELERY_WORKER_EXTRA_ARGS:-}" ]; then
    echo "Appending extra Celery worker args: ${CELERY_WORKER_EXTRA_ARGS}."
    # shellcheck disable=SC2086
    set -- "$@" ${CELERY_WORKER_EXTRA_ARGS}
fi

echo "Starting Celery worker for recommendations queue (queues=${queues}, loglevel=${log_level})..."
echo "Command: $*"
exec "$@"

