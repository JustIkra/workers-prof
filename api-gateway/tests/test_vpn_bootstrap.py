from __future__ import annotations

from pathlib import Path

import pytest

from app.core import vpn_bootstrap as vpn


class FakeResult:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_bootstrap_from_env_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_ensure(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(vpn, "ensure_wireguard_up", fake_ensure)

    executed = vpn.bootstrap_from_env({"VPN_ENABLED": "0"})

    assert executed is False
    assert called is False


def test_bootstrap_from_env_requires_config_when_enabled() -> None:
    with pytest.raises(vpn.WireGuardBootstrapError):
        vpn.bootstrap_from_env({"VPN_ENABLED": "1"})


def test_bootstrap_from_env_calls_helper(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "wg0.conf"
    cfg.write_text("[Interface]\n")

    captured: dict[str, str] = {}
    configured: dict[str, object] = {}

    def fake_ensure(path: str, interface: str, **_kwargs):
        captured["path"] = path
        captured["interface"] = interface

    def fake_default_route():
        return vpn.DefaultRoute(gateway="172.20.0.1", dev="eth0")

    def fake_configure(interface: str, env: dict[str, str], route):
        configured["interface"] = interface
        configured["env"] = env
        configured["route"] = route

    monkeypatch.setattr(vpn, "ensure_wireguard_up", fake_ensure)
    monkeypatch.setattr(vpn, "_get_default_route", fake_default_route)
    monkeypatch.setattr(vpn, "configure_split_tunnel", fake_configure)

    executed = vpn.bootstrap_from_env(
        {
            "VPN_ENABLED": "1",
            "VPN_TYPE": "wireguard",
            "WG_CONFIG_PATH": str(cfg),
            "WG_INTERFACE": "wg-test",
        }
    )

    assert executed is True
    assert captured == {"path": str(cfg), "interface": "wg-test"}
    assert configured["interface"] == "wg-test"
    assert configured["route"] == fake_default_route()


def test_ensure_wireguard_up_skips_when_interface_ready(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "wg0.conf"
    cfg.write_text("[Interface]\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    calls: list[list[str]] = []

    def fake_run(cmd, capture_output=True, text=True):
        calls.append(cmd)
        assert capture_output is True
        assert text is True
        if cmd[0] == "ip":
            return FakeResult(stdout="wg0: <POINTOPOINT,UP,LOWER_UP> mtu 1420 state UP")
        raise AssertionError("wg-quick should not be invoked when interface is already up")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    vpn.ensure_wireguard_up(str(cfg), "wg0", timeout=0.1, poll_interval=0.01)

    assert calls and calls[0][0] == "ip"


def test_ensure_wireguard_up_invokes_wg_quick(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "wg0.conf"
    cfg.write_text("[Interface]\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    calls: list[list[str]] = []
    ip_invocations = 0

    def fake_run(cmd, capture_output=True, text=True):
        nonlocal ip_invocations
        calls.append(cmd)
        if cmd[0] == "ip":
            ip_invocations += 1
            if ip_invocations == 1:
                return FakeResult(returncode=1, stderr="not found")
            return FakeResult(stdout="wg0: <POINTOPOINT,UP,LOWER_UP> mtu 1420 state UP")
        if cmd[0] == "wg-quick":
            return FakeResult()
        raise AssertionError("Unexpected command")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    vpn.ensure_wireguard_up(str(cfg), "wg0", timeout=0.2, poll_interval=0.01)

    assert any(call[0] == "wg-quick" for call in calls)
    assert ip_invocations >= 2


def test_ensure_wireguard_up_raises_when_wg_quick_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "wg0.conf"
    cfg.write_text("[Interface]\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(cmd, capture_output=True, text=True):
        if cmd[0] == "ip":
            return FakeResult(returncode=1)
        if cmd[0] == "wg-quick":
            return FakeResult(returncode=1, stderr="boom")
        raise AssertionError("Unexpected command")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    with pytest.raises(vpn.WireGuardBootstrapError):
        vpn.ensure_wireguard_up(str(cfg), "wg0", timeout=0.1, poll_interval=0.01)


def test_ensure_wireguard_up_times_out(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "wg0.conf"
    cfg.write_text("[Interface]\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(cmd, capture_output=True, text=True):
        if cmd[0] == "ip":
            return FakeResult(returncode=1, stderr="down")
        if cmd[0] == "wg-quick":
            return FakeResult()
        raise AssertionError("Unexpected command")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    with pytest.raises(vpn.WireGuardBootstrapError):
        vpn.ensure_wireguard_up(str(cfg), "wg0", timeout=0.05, poll_interval=0.01)


def test_configure_split_tunnel_all_mode_adds_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, vpn.DefaultRoute]] = []

    def fake_route(target: str, route: vpn.DefaultRoute):
        calls.append((target, route))

    monkeypatch.setattr(vpn, "_ensure_route_via_gateway", fake_route)

    env = {"VPN_ROUTE_MODE": "all", "VPN_BYPASS_CIDRS": "172.16.0.0/12"}
    default = vpn.DefaultRoute(gateway="172.20.0.1", dev="eth0")

    vpn.configure_split_tunnel("wg0", env, default)

    assert calls == [("172.16.0.0/12", default)]


def test_configure_split_tunnel_domains_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    actions: list[str] = []

    def fake_restore(route: vpn.DefaultRoute):
        actions.append(f"restore:{route.dev}")

    def fake_remove(interface: str):
        actions.append(f"remove:{interface}")

    def fake_resolve(domains):
        return ["34.1.1.1", "34.1.1.2"]

    def fake_route_interface(target: str, interface: str):
        actions.append(f"route:{target}:{interface}")

    def fake_route_gateway(target: str, route: vpn.DefaultRoute):
        actions.append(f"bypass:{target}:{route.dev}")

    monkeypatch.setattr(vpn, "_restore_default_route", fake_restore)
    monkeypatch.setattr(vpn, "_remove_default_route_via_interface", fake_remove)
    monkeypatch.setattr(vpn, "_resolve_domains", fake_resolve)
    monkeypatch.setattr(vpn, "_ensure_route_via_interface", fake_route_interface)
    monkeypatch.setattr(vpn, "_ensure_route_via_gateway", fake_route_gateway)

    env = {
        "VPN_ROUTE_MODE": "domains",
        "VPN_ROUTE_DOMAINS": "generativelanguage.googleapis.com",
        "VPN_BYPASS_CIDRS": "10.0.0.0/8",
    }
    default = vpn.DefaultRoute(gateway="172.20.0.1", dev="eth0")

    vpn.configure_split_tunnel("wg0", env, default)

    assert actions == [
        "remove:wg0",
        "restore:eth0",
        "route:34.1.1.1/32:wg0",
        "route:34.1.1.2/32:wg0",
        "bypass:10.0.0.0/8:eth0",
    ]


def test_configure_split_tunnel_requires_domains() -> None:
    default = vpn.DefaultRoute(gateway="172.20.0.1", dev="eth0")

    with pytest.raises(vpn.WireGuardBootstrapError):
        vpn.configure_split_tunnel("wg0", {"VPN_ROUTE_MODE": "domains"}, default)


def test_check_sysctl_param_returns_true_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, capture_output=True, text=True, timeout=None):
        if cmd == ["sysctl", "-n", "net.ipv4.conf.all.src_valid_mark"]:
            return FakeResult(returncode=0, stdout="1\n")
        raise AssertionError("Unexpected command")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    assert vpn._check_sysctl_param("net.ipv4.conf.all.src_valid_mark", "1") is True


def test_check_sysctl_param_returns_false_when_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, capture_output=True, text=True, timeout=None):
        if cmd == ["sysctl", "-n", "net.ipv4.conf.all.src_valid_mark"]:
            return FakeResult(returncode=0, stdout="0\n")
        raise AssertionError("Unexpected command")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    assert vpn._check_sysctl_param("net.ipv4.conf.all.src_valid_mark", "1") is False


def test_check_sysctl_param_returns_false_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, capture_output=True, text=True, timeout=None):
        if cmd == ["sysctl", "-n", "net.ipv4.conf.all.src_valid_mark"]:
            return FakeResult(returncode=1, stderr="error")
        raise AssertionError("Unexpected command")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    assert vpn._check_sysctl_param("net.ipv4.conf.all.src_valid_mark", "1") is False


def test_run_with_sysctl_fallback_succeeds_when_param_already_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that sysctl permission error is ignored when parameter is already set correctly."""
    cmd = ["wg-quick", "up", "/path/to/config.conf"]
    error_stderr = "sysctl: permission denied on key 'net.ipv4.conf.all.src_valid_mark'"

    def fake_run(cmd_arg, capture_output=True, text=True):
        if cmd_arg == cmd:
            return FakeResult(returncode=1, stderr=error_stderr)
        if cmd_arg == ["sysctl", "-n", "net.ipv4.conf.all.src_valid_mark"]:
            return FakeResult(returncode=0, stdout="1\n")
        raise AssertionError(f"Unexpected command: {cmd_arg}")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    result = vpn._run_with_sysctl_fallback(cmd)
    assert result.returncode == 0


def test_run_with_sysctl_fallback_raises_when_param_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that sysctl permission error raises when parameter is not set correctly."""
    cmd = ["wg-quick", "up", "/path/to/config.conf"]
    error_stderr = "sysctl: permission denied on key 'net.ipv4.conf.all.src_valid_mark'"

    def fake_run(cmd_arg, capture_output=True, text=True, timeout=None):
        if cmd_arg == cmd:
            return FakeResult(returncode=1, stderr=error_stderr)
        if cmd_arg == ["sysctl", "-n", "net.ipv4.conf.all.src_valid_mark"]:
            return FakeResult(returncode=0, stdout="0\n")
        raise AssertionError(f"Unexpected command: {cmd_arg}")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    with pytest.raises(vpn.WireGuardBootstrapError, match="Cannot proceed"):
        vpn._run_with_sysctl_fallback(cmd)


def test_run_with_sysctl_fallback_raises_on_non_sysctl_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that non-sysctl errors are raised normally."""
    cmd = ["wg-quick", "up", "/path/to/config.conf"]
    error_stderr = "Interface not found"

    def fake_run(cmd_arg, capture_output=True, text=True):
        if cmd_arg == cmd:
            return FakeResult(returncode=1, stderr=error_stderr)
        raise AssertionError(f"Unexpected command: {cmd_arg}")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    with pytest.raises(vpn.WireGuardBootstrapError, match="Interface not found"):
        vpn._run_with_sysctl_fallback(cmd)


def test_ensure_wireguard_up_handles_sysctl_error_when_param_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test that ensure_wireguard_up succeeds when wg-quick fails with sysctl error but param is set."""
    cfg = tmp_path / "wg0.conf"
    cfg.write_text("[Interface]\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    ip_invocations = 0
    sysctl_checked = False

    def fake_run(cmd, capture_output=True, text=True, timeout=None):
        nonlocal ip_invocations, sysctl_checked
        if cmd[0] == "ip":
            ip_invocations += 1
            if ip_invocations == 1:
                return FakeResult(returncode=1, stderr="not found")
            return FakeResult(stdout="wg0: <POINTOPOINT,UP,LOWER_UP> mtu 1420 state UP")
        if cmd[0] == "wg-quick":
            return FakeResult(
                returncode=1,
                stderr="sysctl: permission denied on key 'net.ipv4.conf.all.src_valid_mark'",
            )
        if cmd == ["sysctl", "-n", "net.ipv4.conf.all.src_valid_mark"]:
            sysctl_checked = True
            return FakeResult(returncode=0, stdout="1\n")
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    vpn.ensure_wireguard_up(str(cfg), "wg0", timeout=0.2, poll_interval=0.01)

    assert sysctl_checked is True


def test_bootstrap_from_env_openvpn_calls_helper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "openvpn.ovpn"
    cfg.write_text("client\ndev tun\n")

    captured: dict[str, str] = {}
    configured: dict[str, object] = {}

    def fake_ensure(path: str, interface: str, **_kwargs):
        captured["path"] = path
        captured["interface"] = interface

    def fake_default_route():
        return vpn.DefaultRoute(gateway="172.20.0.1", dev="eth0")

    def fake_configure(interface: str, env: dict[str, str], route):
        configured["interface"] = interface
        configured["env"] = env
        configured["route"] = route

    monkeypatch.setattr(vpn, "ensure_openvpn_up", fake_ensure)
    monkeypatch.setattr(vpn, "_get_default_route", fake_default_route)
    monkeypatch.setattr(vpn, "configure_split_tunnel", fake_configure)

    executed = vpn.bootstrap_from_env(
        {
            "VPN_ENABLED": "1",
            "VPN_TYPE": "openvpn",
            "OPENVPN_CONFIG_PATH": str(cfg),
            "OPENVPN_INTERFACE": "tun0",
        }
    )

    assert executed is True
    assert captured == {"path": str(cfg), "interface": "tun0"}
    assert configured["interface"] == "tun0"
    assert configured["route"] == fake_default_route()


def test_bootstrap_from_env_openvpn_requires_config() -> None:
    with pytest.raises(vpn.WireGuardBootstrapError, match="OPENVPN_CONFIG_PATH"):
        vpn.bootstrap_from_env(
            {
                "VPN_ENABLED": "1",
                "VPN_TYPE": "openvpn",
            }
        )


def test_bootstrap_from_env_openvpn_unsupported_type() -> None:
    with pytest.raises(vpn.WireGuardBootstrapError, match="Unsupported VPN_TYPE"):
        vpn.bootstrap_from_env(
            {
                "VPN_ENABLED": "1",
                "VPN_TYPE": "invalid",
            }
        )


def test_ensure_openvpn_up_skips_when_interface_ready(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "openvpn.ovpn"
    cfg.write_text("client\ndev tun\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    calls: list[list[str]] = []

    def fake_run(cmd, capture_output=True, text=True):
        calls.append(cmd)
        assert capture_output is True
        assert text is True
        if cmd[0] == "ip":
            return FakeResult(stdout="tun0: <POINTOPOINT,UP,LOWER_UP> mtu 1500 state UP")
        raise AssertionError("openvpn should not be invoked when interface is already up")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    vpn.ensure_openvpn_up(str(cfg), "tun0", timeout=0.1, poll_interval=0.01)

    assert calls and calls[0][0] == "ip"


def test_ensure_openvpn_up_invokes_openvpn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "openvpn.ovpn"
    cfg.write_text("client\ndev tun\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    calls: list[list[str]] = []
    ip_invocations = 0

    def fake_run(cmd, capture_output=True, text=True):
        nonlocal ip_invocations
        calls.append(cmd)
        if cmd[0] == "ip":
            ip_invocations += 1
            if ip_invocations == 1:
                return FakeResult(returncode=1, stderr="not found")
            return FakeResult(stdout="tun0: <POINTOPOINT,UP,LOWER_UP> mtu 1500 state UP")
        if cmd[0] == "openvpn":
            return FakeResult()
        raise AssertionError("Unexpected command")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    vpn.ensure_openvpn_up(str(cfg), "tun0", timeout=0.2, poll_interval=0.01)

    assert any(call[0] == "openvpn" for call in calls)
    assert ip_invocations >= 2


def test_ensure_openvpn_up_raises_when_openvpn_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "openvpn.ovpn"
    cfg.write_text("client\ndev tun\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(cmd, capture_output=True, text=True):
        if cmd[0] == "ip":
            return FakeResult(returncode=1)
        if cmd[0] == "openvpn":
            return FakeResult(returncode=1, stderr="boom")
        raise AssertionError("Unexpected command")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    with pytest.raises(vpn.WireGuardBootstrapError):
        vpn.ensure_openvpn_up(str(cfg), "tun0", timeout=0.1, poll_interval=0.01)


def test_ensure_openvpn_up_times_out(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "openvpn.ovpn"
    cfg.write_text("client\ndev tun\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(cmd, capture_output=True, text=True):
        if cmd[0] == "ip":
            return FakeResult(returncode=1, stderr="down")
        if cmd[0] == "openvpn":
            return FakeResult()
        raise AssertionError("Unexpected command")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)

    with pytest.raises(vpn.WireGuardBootstrapError):
        vpn.ensure_openvpn_up(str(cfg), "tun0", timeout=0.05, poll_interval=0.01)


def test_ensure_openvpn_up_handles_already_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test that ensure_openvpn_up handles case when OpenVPN is already running."""
    cfg = tmp_path / "openvpn.ovpn"
    cfg.write_text("client\ndev tun\n")

    monkeypatch.setattr(vpn.shutil, "which", lambda name: f"/usr/bin/{name}")

    ip_invocations = 0

    def fake_run(cmd, capture_output=True, text=True):
        nonlocal ip_invocations
        if cmd[0] == "ip":
            ip_invocations += 1
            if ip_invocations == 1:
                return FakeResult(returncode=1, stderr="not found")
            # Interface comes up after error
            return FakeResult(stdout="tun0: <POINTOPOINT,UP,LOWER_UP> mtu 1500 state UP")
        if cmd[0] == "openvpn":
            # OpenVPN returns error (already running), but interface comes up
            return FakeResult(returncode=1, stderr="already running")
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(vpn.subprocess, "run", fake_run)
    monkeypatch.setattr(vpn.time, "sleep", lambda _: None)  # Skip sleep

    vpn.ensure_openvpn_up(str(cfg), "tun0", timeout=0.2, poll_interval=0.01)

    assert ip_invocations >= 2
