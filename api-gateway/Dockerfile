# syntax=docker/dockerfile:1.6

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# System deps (curl for healthcheck)
# Note: resolvconf may fail to configure /etc/resolv.conf in Docker, but it's not critical
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        iproute2 \
        iptables \
        wireguard-tools \
        libgomp1 \
        libglib2.0-0 \
    && (DEBIAN_FRONTEND=noninteractive apt-get install -y resolvconf || true) \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy application code (includes entrypoint scripts)
COPY . .

# Create storage dir for file uploads (if not mounted)
RUN mkdir -p /app/storage

# Ensure entrypoint scripts exist and are executable
RUN test -f /app/docker-entrypoint.sh && test -f /app/docker-entrypoint-worker.sh && \
    chmod +x /app/docker-entrypoint.sh /app/docker-entrypoint-worker.sh || \
    (echo "ERROR: Entrypoint scripts not found!" && ls -la /app/docker-entrypoint* && exit 1)

# Expose internal app port (external mapping is controlled by compose)
EXPOSE 9187

# Default environment
ENV ENV=prod \
    APP_PORT=9187 \
    FILE_STORAGE_BASE=/app/storage

# Healthcheck hits FastAPI health endpoint
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD curl -fsS http://127.0.0.1:${APP_PORT}/api/healthz || exit 1

# Default command kept for non-compose usage (e.g., worker)
CMD ["python", "main.py"]
