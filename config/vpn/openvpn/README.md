# OpenVPN Configuration

Place your OpenVPN config file here (never commit secrets). The app container should bring up VPN before starting when `VPN_ENABLED=1` and `VPN_TYPE=openvpn`.

## OpenVPN Configuration

Expected files:
- `openvpn.ovpn` — main OpenVPN config file (see `openvpn.conf.example`)

The `.ovpn` file format is a text file that typically contains:
- Client configuration directives
- Embedded CA certificate (`<ca>` section)
- Client certificate (`<cert>` section)
- Client private key (`<key>` section)
- TLS authentication key (`<tls-auth>` section)

**Important**: Never commit real certificates, keys, or configuration files with secrets to version control.

## Environment Variables

### OpenVPN-Specific
- `VPN_ENABLED=1` — Enable VPN
- `VPN_TYPE=openvpn` — Set VPN type to OpenVPN
- `OPENVPN_CONFIG_PATH=/run/vpn/openvpn/openvpn.ovpn` — Path to OpenVPN config file
- `OPENVPN_INTERFACE=tun0` — Interface name (default: `tun0`)

### Common Routing Options
- `VPN_ROUTE_MODE=domains` — Routing mode (allowed: `all|domains|cidr`)
- `VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com` — Domains to route via VPN (when `VPN_ROUTE_MODE=domains`)
- `VPN_ROUTE_CIDRS=` — CIDRs to route via VPN (when `VPN_ROUTE_MODE=cidr`, example: `34.110.0.0/16`)
- `VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16` — CIDRs to bypass VPN

## Split-Tunnel Configuration

OpenVPN supports split-tunnel routing similar to WireGuard. The bootstrap script uses `--route-nopull` to prevent OpenVPN from automatically changing the default route, allowing manual route configuration via `configure_split_tunnel()`.

**Important**: If your OpenVPN config contains `redirect-gateway`, it will be ignored when using `--route-nopull`. Routes are configured manually by the application.

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

## Interface Details

OpenVPN uses TUN (Tunnel) interfaces, typically named `tun0`, `tun1`, etc. The interface name can be specified via `OPENVPN_INTERFACE` environment variable.

Unlike WireGuard (`wg0`), OpenVPN interfaces are created dynamically when the connection is established.

## Verification

Run inside the app container after `VPN_ENABLED=1` and `VPN_TYPE=openvpn`:

```bash
# Check interface status
ip link show dev tun0

# Check routes
ip route show

# Test connectivity through VPN
curl -v https://generativelanguage.googleapis.com/
```

## Notes

- Split‑tunnel keeps Gemini traffic inside VPN while Docker-internal services stay on the default bridge.
- Health endpoint (`/api/vpn/health`) verifies interface up and reachability of Gemini via VPN.
- Keys and real configs must be supplied privately by the operator.
- OpenVPN requires root privileges to create TUN interfaces (usually available in Docker containers).
- PID files are stored in `/var/run/openvpn/` for process management.

