# AWG (AmneziaWG) VPN Configuration

AWG is a WireGuard fork with obfuscation support for enhanced privacy and bypass capabilities.

## Configuration File

Expected files:
- `awg0.conf` — main interface config (see `awg0.conf.example`)
- Private/public keys referenced by `awg0.conf` (do not commit private keys)

## Required Parameters

AWG configuration requires the following obfuscation parameters in the `[Interface]` section:

- `Jc` — Obfuscation parameter
- `Jmin` — Minimum obfuscation interval
- `Jmax` — Maximum obfuscation interval
- `S1` — Obfuscation seed 1
- `S2` — Obfuscation seed 2
- `H1` — Obfuscation hash 1
- `H2` — Obfuscation hash 2
- `H3` — Obfuscation hash 3
- `H4` — Obfuscation hash 4

All standard WireGuard parameters are also supported (Address, DNS, PrivateKey, etc.).

## Environment Variables

- `VPN_ENABLED=1` — Enable VPN
- `VPN_TYPE=awg` — Use AWG instead of WireGuard
- `WG_CONFIG_PATH=/run/vpn/awg/awg0.conf` — Path to AWG config file
- `WG_INTERFACE=awg0` — Interface name (default: `awg0` for AWG)
- `VPN_ROUTE_MODE=domains` — Routing mode (allowed: `all|domains|cidr`)
- `VPN_ROUTE_DOMAINS=generativelanguage.googleapis.com` — Domains to route via AWG
- `VPN_BYPASS_CIDRS=172.16.0.0/12,10.0.0.0/8,192.168.0.0/16` — CIDRs to bypass VPN

## Client Requirements

For full obfuscation support, the `amneziawg` client is required. If not available, the system falls back to `wg-quick`, but obfuscation may not work.

The bootstrap script will:
1. Check for `amneziawg` client availability
2. Use `amneziawg` if found (full obfuscation support)
3. Fall back to `wg-quick` if not found (basic WireGuard functionality, obfuscation disabled)

## Validation

The bootstrap script validates AWG configs to ensure all required obfuscation parameters are present. Missing parameters will cause bootstrap to fail with a clear error message.

## Example Configuration

See `awg0.conf.example` for a complete example with all required parameters.

## Notes

- AWG uses the same protocol as WireGuard but with additional obfuscation layers
- Split-tunnel routing works the same way as WireGuard
- Health endpoint (`/api/vpn/health`) supports AWG interfaces
- Keys and real configs must be supplied privately by the operator

