from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


class WireGuardBootstrapError(RuntimeError):
    """Raised when WireGuard bootstrap fails."""


@dataclass
class DefaultRoute:
    gateway: str
    dev: str
    metric: str | None = None


def _log(message: str) -> None:
    print(f"[vpn] {message}", flush=True)


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise WireGuardBootstrapError(
            f"'{name}' binary not found. Install wireguard-tools inside the container."
        )


def _run_or_raise(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or f"exit code {result.returncode}"
        raise WireGuardBootstrapError(f"Command '{' '.join(cmd)}' failed: {details}")
    return result


def _run_ignore(cmd: Sequence[str]) -> None:
    subprocess.run(cmd, capture_output=True, text=True)


def _interface_up(interface: str) -> bool:
    result = subprocess.run(
        ["ip", "link", "show", "dev", interface],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False

    output = result.stdout or ""
    if "state UP" in output:
        return True

    if "<" in output and ">" in output:
        flags = output.split("<", 1)[1].split(">", 1)[0]
        flag_set = {flag.strip() for flag in flags.split(",")}
        return "UP" in flag_set or "LOWER_UP" in flag_set

    return False


def _wait_for_interface(interface: str, timeout: float, poll_interval: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _interface_up(interface):
            return
        time.sleep(poll_interval)
    raise WireGuardBootstrapError(
        f"WireGuard interface '{interface}' did not become available within {timeout:.1f}s"
    )


def _parse_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_default_route() -> DefaultRoute | None:
    result = subprocess.run(
        ["ip", "route", "show", "default"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    line = (result.stdout or "").strip().splitlines()
    if not line:
        return None
    tokens = line[0].split()
    gateway = None
    dev = None
    metric = None
    for idx, token in enumerate(tokens):
        if token == "via" and idx + 1 < len(tokens):
            gateway = tokens[idx + 1]
        elif token == "dev" and idx + 1 < len(tokens):
            dev = tokens[idx + 1]
        elif token == "metric" and idx + 1 < len(tokens):
            metric = tokens[idx + 1]
    if gateway and dev:
        return DefaultRoute(gateway=gateway, dev=dev, metric=metric)
    return None


def _restore_default_route(route: DefaultRoute) -> None:
    cmd = ["ip", "route", "replace", "default", "via", route.gateway, "dev", route.dev]
    if route.metric:
        cmd.extend(["metric", route.metric])
    _run_or_raise(cmd)


def _remove_default_route_via_interface(interface: str) -> None:
    _run_ignore(["ip", "route", "del", "default", "dev", interface])


def _ensure_route_via_gateway(target: str, route: DefaultRoute) -> None:
    cmd = ["ip", "route", "replace", target, "via", route.gateway, "dev", route.dev]
    _run_or_raise(cmd)


def _ensure_route_via_interface(target: str, interface: str) -> None:
    cmd = ["ip", "route", "replace", target, "dev", interface]
    _run_or_raise(cmd)


def _resolve_domains(domains: Iterable[str]) -> list[str]:
    addresses: list[str] = []
    seen: set[str] = set()
    for domain in domains:
        try:
            infos = socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:  # pragma: no cover - depends on DNS
            raise WireGuardBootstrapError(f"Failed to resolve domain '{domain}': {exc}") from exc
        for info in infos:
            ip = info[4][0]
            if ":" in ip:
                continue  # skip IPv6 for now
            if ip not in seen:
                addresses.append(ip)
                seen.add(ip)
    if not addresses:
        raise WireGuardBootstrapError(
            f"DNS lookup for {', '.join(domains)} returned no IPv4 addresses."
        )
    return addresses


def configure_split_tunnel(
    interface: str,
    env: Mapping[str, str],
    default_route: DefaultRoute | None,
) -> None:
    route_mode = env.get("VPN_ROUTE_MODE", "domains").strip().lower()
    if route_mode not in {"all", "domains", "cidr"}:
        raise WireGuardBootstrapError("VPN_ROUTE_MODE must be one of: all, domains, cidr.")

    bypass_cidrs = _parse_csv(env.get("VPN_BYPASS_CIDRS"))

    if route_mode == "all":
        _log("Routing mode 'all' – entire outbound traffic locked to WireGuard.")
        if bypass_cidrs:
            if default_route is None:
                raise WireGuardBootstrapError(
                    "Cannot add bypass CIDRs without baseline default route."
                )
            for cidr in bypass_cidrs:
                _log(f"Adding bypass CIDR via original gateway: {cidr}")
                _ensure_route_via_gateway(cidr, default_route)
        return

    if default_route is None:
        raise WireGuardBootstrapError(
            "Split-tunnel mode requires detecting the original default route."
        )

    if route_mode == "domains":
        domains = _parse_csv(env.get("VPN_ROUTE_DOMAINS"))
        if not domains:
            raise WireGuardBootstrapError(
                "VPN_ROUTE_DOMAINS must be provided when VPN_ROUTE_MODE=domains."
            )
        targets = [f"{ip}/32" for ip in _resolve_domains(domains)]
    else:
        cidrs = _parse_csv(env.get("VPN_ROUTE_CIDRS"))
        if not cidrs:
            raise WireGuardBootstrapError(
                "VPN_ROUTE_CIDRS must be provided when VPN_ROUTE_MODE=cidr."
            )
        targets = cidrs

    _remove_default_route_via_interface(interface)
    _restore_default_route(default_route)
    _log(
        "Default route restored to original gateway; only selected destinations "
        f"will use WireGuard ({interface})."
    )

    for target in targets:
        _log(f"Routing {target} via {interface}")
        _ensure_route_via_interface(target, interface)

    for cidr in bypass_cidrs:
        _log(f"Ensuring bypass CIDR stays on original gateway: {cidr}")
        _ensure_route_via_gateway(cidr, default_route)


def ensure_wireguard_up(
    config_path: str,
    interface: str,
    *,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> None:
    """
    Bring WireGuard interface up using the provided config file.
    """
    _require_binary("wg-quick")
    _require_binary("ip")

    cfg = Path(config_path)
    if not cfg.exists():
        raise WireGuardBootstrapError(f"WireGuard config not found: {cfg}")

    _log(f"Ensuring WireGuard interface '{interface}' is up (config={cfg})")

    if _interface_up(interface):
        _log(f"WireGuard interface '{interface}' already up – skipping wg-quick.")
        return

    _run_or_raise(["wg-quick", "up", str(cfg)])
    _wait_for_interface(interface, timeout, poll_interval)
    _log(f"WireGuard interface '{interface}' is up.")


def bootstrap_from_env(
    env: Mapping[str, str] | None = None,
    *,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> bool:
    """
    Bootstrap WireGuard using environment variables.

    Returns True when VPN enforcement executed, False when skipped.
    """
    data = env or os.environ
    if not _is_truthy(data.get("VPN_ENABLED", "0")):
        _log("VPN disabled; skipping WireGuard bootstrap.")
        return False

    vpn_type = data.get("VPN_TYPE", "wireguard").lower()
    if vpn_type != "wireguard":
        raise WireGuardBootstrapError(f"Unsupported VPN_TYPE '{vpn_type}'.")

    config_path = data.get("WG_CONFIG_PATH")
    interface = data.get("WG_INTERFACE", "wg0")

    if not config_path:
        raise WireGuardBootstrapError("WG_CONFIG_PATH is required when VPN_ENABLED=1.")

    default_route = _get_default_route()

    ensure_wireguard_up(
        config_path,
        interface,
        timeout=timeout,
        poll_interval=poll_interval,
    )

    configure_split_tunnel(interface, data, default_route)
    return True


def main() -> int:
    try:
        ran = bootstrap_from_env()
        if ran:
            _log("WireGuard bootstrap completed successfully.")
        return 0
    except WireGuardBootstrapError as exc:
        _log(f"WireGuard bootstrap failed: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - safety net
        _log(f"Unexpected VPN bootstrap error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
