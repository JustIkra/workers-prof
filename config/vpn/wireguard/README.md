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
- `VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16`

Notes:
- Split‑tunnel: only Gemini traffic goes via WireGuard; DB/cache/queue stay on local Docker network.
- Health endpoint should verify interface up and reachability of Gemini via VPN.
- Keys and real configs must be supplied privately by the operator.

