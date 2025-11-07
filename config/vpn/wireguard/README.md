# WireGuard VPN (inside container)

Place your WireGuard config here (never commit secrets). The app container should bring up WireGuard before starting when `VPN_ENABLED=1`.

Expected files:
- `wg0.conf` — main interface config (see `wg0.conf.example`)
- Private/public keys referenced by `wg0.conf` (do not commit private keys)

Environment (maps to app):
- `VPN_ENABLED=1`
- `VPN_TYPE=wireguard`
- `WG_CONFIG_PATH=/run/vpn/wireguard/wg0.conf`
- `WG_INTERFACE=wg0`
- `VPN_ROUTE_MODE=domains` (allowed: `all|domains|cidr`)
- `VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com` (Gemini endpoint)
- `VPN_ROUTE_CIDRS=` (only when `VPN_ROUTE_MODE=cidr`, example: `34.110.0.0/16`)
- `VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16`

## Routing profiles

| Mode      | Description                                                                                       |
|-----------|---------------------------------------------------------------------------------------------------|
| `all`     | Default route switched to WireGuard. Use `VPN_BYPASS_CIDRS` to keep Docker networks reachable.    |
| `domains` | Default route stays on Docker/host; only domains listed in `VPN_ROUTE_DOMAINS` go via WireGuard.  |
| `cidr`    | Default route stays on Docker/host; explicit CIDRs from `VPN_ROUTE_CIDRS` go via WireGuard.       |

Recommended settings for split‑tunnel Gemini access:
- `VPN_ROUTE_MODE=domains`
- `VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com`
- `VPN_BYPASS_CIDRS` includes Docker subnets (`172.16.0.0/12`, `10.0.0.0/8`, `192.168.0.0/16`) so DB/cache stay reachable.

## Verification script

Run inside the app container after `VPN_ENABLED=1`:

```bash
./scripts/vpn/check_routes.sh generativelanguage.googleapis.com 172.20.0.2
```

- Ensures the Gemini endpoint resolves to an IP that routes through `wg0`.
- Performs a `curl https://generativelanguage.googleapis.com/` probe (expect 401/403 without API key, but it must succeed over the tunnel).
- Checks that the second argument (e.g., PostgreSQL at `172.20.0.2`) **does not** leave via `wg0`.

## Notes

- Split‑tunnel keeps Gemini traffic inside WireGuard while Docker-internal services stay on the default bridge.
- Health endpoint should verify interface up and reachability of Gemini via VPN.
- Keys and real configs must be supplied privately by the operator.
