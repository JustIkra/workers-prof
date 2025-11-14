# WireGuard / AWG VPN (inside container)

Place your WireGuard or AWG config here (never commit secrets). The app container should bring up VPN before starting when `VPN_ENABLED=1`.

**Note**: The project also supports OpenVPN. See `../openvpn/README.md` for OpenVPN configuration.

## WireGuard Configuration

Expected files:
- `wg0.conf` — main interface config (see `wg0.conf.example`)
- Private/public keys referenced by `wg0.conf` (do not commit private keys)

## AWG (AmneziaWG) Configuration

AWG is a WireGuard fork with obfuscation support. Expected files:
- `awg0.conf` — main interface config (see `../awg/awg0.conf.example`)
- Private/public keys referenced by `awg0.conf` (do not commit private keys)
- **Required obfuscation parameters**: Jc, Jmin, Jmax, S1, S2, H1, H2, H3, H4 in `[Interface]` section

## Environment Variables

### Common (WireGuard and AWG)
- `VPN_ENABLED=1` — Enable VPN
- `VPN_TYPE=wireguard|awg|openvpn` — VPN type (default: `wireguard`)
- `WG_CONFIG_PATH=/run/vpn/wireguard/wg0.conf` — Path to config file
- `WG_INTERFACE=wg0` — Interface name (default: `wg0` for WireGuard, `awg0` for AWG)
- `VPN_ROUTE_MODE=domains` — Routing mode (allowed: `all|domains|cidr`)
- `VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com` — Domains to route via VPN (when `VPN_ROUTE_MODE=domains`)
- `VPN_ROUTE_CIDRS=` — CIDRs to route via VPN (when `VPN_ROUTE_MODE=cidr`, example: `34.110.0.0/16`)
- `VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16` — CIDRs to bypass VPN

### AWG-Specific Notes
- AWG requires a specialized client (`amneziawg`) for full obfuscation support
- If `amneziawg` client is not available, the system falls back to `wg-quick` (obfuscation may not work)
- AWG config must include all obfuscation parameters (Jc, Jmin, Jmax, S1, S2, H1-H4) in the `[Interface]` section

## Routing Profiles

| Mode      | Description                                                                                       |
|-----------|---------------------------------------------------------------------------------------------------|
| `all`     | Default route switched to VPN. Use `VPN_BYPASS_CIDRS` to keep Docker networks reachable.         |
| `domains` | Default route stays on Docker/host; only domains listed in `VPN_ROUTE_DOMAINS` go via VPN.      |
| `cidr`    | Default route stays on Docker/host; explicit CIDRs from `VPN_ROUTE_CIDRS` go via VPN.            |

Recommended settings for split‑tunnel Gemini access:
- `VPN_ROUTE_MODE=domains`
- `VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com`
- `VPN_BYPASS_CIDRS` includes Docker subnets (`172.16.0.0/12`, `10.0.0.0/8`, `192.168.0.0/16`) so DB/cache stay reachable.

## Verification Script

Run inside the app container after `VPN_ENABLED=1`:

```bash
./scripts/vpn/check_routes.sh generativelanguage.googleapis.com 172.20.0.2
```

- Ensures the Gemini endpoint resolves to an IP that routes through VPN interface.
- Performs a `curl https://generativelanguage.googleapis.com/` probe (expect 401/403 without API key, but it must succeed over the tunnel).
- Checks that the second argument (e.g., PostgreSQL at `172.20.0.2`) **does not** leave via VPN interface.

## Notes

- Split‑tunnel keeps Gemini traffic inside VPN while Docker-internal services stay on the default bridge.
- Health endpoint (`/api/vpn/health`) verifies interface up and reachability of Gemini via VPN.
- Keys and real configs must be supplied privately by the operator.
- For AWG: Full obfuscation requires `amneziawg` client. Fallback to `wg-quick` works but obfuscation may be disabled.
