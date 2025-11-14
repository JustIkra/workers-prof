#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-generativelanguage.googleapis.com}"
BYPASS_TARGET="${2:-172.20.0.2}"
WG_IFACE="${WG_INTERFACE:-wg0}"

if ! command -v ip >/dev/null 2>&1; then
    echo "[vpn-check] 'ip' binary missing." >&2
    exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "[vpn-check] 'curl' binary missing." >&2
    exit 1
fi

lookup() {
    getent hosts "$1" 2>/dev/null | awk 'NR==1 {print $1}'
}

DOMAIN_IP=$(lookup "$DOMAIN" || true)
if [[ -z "${DOMAIN_IP:-}" ]]; then
    echo "[vpn-check] unable to resolve ${DOMAIN}" >&2
    exit 1
fi

echo "[vpn-check] Probing $DOMAIN ($DOMAIN_IP) via ${WG_IFACE}"
ROUTE_OUTPUT=$(ip route get "$DOMAIN_IP")
echo "$ROUTE_OUTPUT"
if ! grep -q "dev ${WG_IFACE}" <<<"$ROUTE_OUTPUT"; then
    echo "[vpn-check] expected traffic to ${DOMAIN} to use ${WG_IFACE}" >&2
    exit 2
fi

echo "[vpn-check] TLS probe through VPN (expect HTTP 401/403 from Gemini)"
curl -sS --max-time 5 --connect-timeout 5 "https://${DOMAIN}/" >/dev/null || {
    echo "[vpn-check] curl to ${DOMAIN} failed" >&2
    exit 3
}

if [[ -n "${BYPASS_TARGET:-}" ]]; then
    echo "[vpn-check] Probing bypass target ${BYPASS_TARGET}"
    BYPASS_ROUTE=$(ip route get "$BYPASS_TARGET")
    echo "$BYPASS_ROUTE"
    if grep -q "dev ${WG_IFACE}" <<<"$BYPASS_ROUTE"; then
        echo "[vpn-check] expected ${BYPASS_TARGET} to stay off ${WG_IFACE}" >&2
        exit 4
    fi
fi

echo "[vpn-check] Split tunnel routing looks good."
