"""
Tests for /api/vpn/health (VPN-03).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import get_db
from app.schemas.vpn import (
    GeminiProbeResult,
    GeminiProbeStatus,
    InterfaceStatus,
    RouteEntry,
    VpnHealthStatus,
    WireGuardOverview,
    VpnPeer,
)
from app.services import vpn_health as service
from main import app


@pytest.fixture
async def vpn_client():
    """HTTP client that bypasses database dependency for VPN diagnostics."""

    async def noop_db():
        yield None

    app.dependency_overrides[get_db] = noop_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_vpn_health_ok(
    test_env,
    vpn_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """Healthy VPN returns 200 with aggregated diagnostics."""
    monkeypatch.setattr(settings, "vpn_enabled", True)
    monkeypatch.setattr(settings, "allow_external_network", True)

    mock_interface = InterfaceStatus(
        name="wg0",
        is_up=True,
        state="UP",
        addresses=["10.1.0.2/32"],
    )
    mock_wireguard = WireGuardOverview(
        interface="wg0",
        public_key="pubkey",
        listen_port=51820,
        peers=[
            VpnPeer(
                public_key="peer1",
                allowed_ips=["10.2.0.2/32"],
                latest_handshake="5 seconds ago",
            )
        ],
    )
    mock_routes = [
        RouteEntry(
            destination="34.110.0.0/16",
            dev="wg0",
            via=None,
            metric=None,
            raw="34.110.0.0/16 dev wg0 scope link",
        )
    ]
    mock_probe = GeminiProbeResult(
        domain="generativelanguage.googleapis.com",
        status=GeminiProbeStatus.OK,
        http_status=403,
        latency_ms=12.5,
    )

    monkeypatch.setattr(service, "collect_interface_status", lambda *_: mock_interface)
    monkeypatch.setattr(service, "collect_wireguard_overview", lambda *_: mock_wireguard)
    monkeypatch.setattr(service, "collect_routes", lambda *_: mock_routes)

    async def fake_probe(*_, **__):
        return mock_probe

    monkeypatch.setattr(service, "perform_gemini_probe", fake_probe)

    response = await vpn_client.get("/api/vpn/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == VpnHealthStatus.HEALTHY.value
    assert data["interface"]["is_up"] is True
    assert data["probe"]["status"] == GeminiProbeStatus.OK.value


@pytest.mark.asyncio
async def test_vpn_health_probe_failure_returns_503(
    test_env,
    vpn_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """Probe failure propagates degraded status with 503."""
    monkeypatch.setattr(settings, "vpn_enabled", True)
    monkeypatch.setattr(settings, "allow_external_network", True)

    mock_interface = InterfaceStatus(name="wg0", is_up=True)
    mock_wireguard = WireGuardOverview(interface="wg0")
    mock_routes: list[RouteEntry] = []
    mock_probe = GeminiProbeResult(
        domain="generativelanguage.googleapis.com",
        status=GeminiProbeStatus.FAIL,
        error="timeout",
    )

    monkeypatch.setattr(service, "collect_interface_status", lambda *_: mock_interface)
    monkeypatch.setattr(service, "collect_wireguard_overview", lambda *_: mock_wireguard)
    monkeypatch.setattr(service, "collect_routes", lambda *_: mock_routes)

    async def fake_probe(*_, **__):
        return mock_probe

    monkeypatch.setattr(service, "perform_gemini_probe", fake_probe)

    response = await vpn_client.get("/api/vpn/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == VpnHealthStatus.DEGRADED.value
    assert mock_probe.error in data["details"][0]


@pytest.mark.asyncio
async def test_vpn_health_disabled_configuration(
    test_env,
    vpn_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """VPN disabled returns disabled status without hitting system commands."""
    monkeypatch.setattr(settings, "vpn_enabled", False)

    response = await vpn_client.get("/api/vpn/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == VpnHealthStatus.DISABLED.value
    assert data["details"][0] == "VPN disabled in configuration."
