"""
VPN diagnostic response schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class VpnPeer(BaseModel):
    """WireGuard peer information."""

    public_key: str
    endpoint: str | None = None
    allowed_ips: list[str] = Field(default_factory=list)
    latest_handshake: str | None = None
    transfer_rx_bytes: int | None = None
    transfer_tx_bytes: int | None = None
    persistent_keepalive: str | None = None


class WireGuardOverview(BaseModel):
    """WireGuard interface summary."""

    interface: str
    public_key: str | None = None
    listen_port: int | None = None
    peers: list[VpnPeer] = Field(default_factory=list)
    error: str | None = None


class InterfaceStatus(BaseModel):
    """Link-layer state for the VPN interface."""

    name: str
    is_up: bool
    state: str | None = None
    addresses: list[str] = Field(default_factory=list)
    error: str | None = None


class RouteEntry(BaseModel):
    """Route table entry that targets the VPN interface."""

    destination: str
    via: str | None = None
    dev: str | None = None
    metric: int | None = None
    raw: str | None = None


class GeminiProbeStatus(str, Enum):
    """Gemini probe outcome."""

    OK = "ok"
    FAIL = "fail"
    SKIPPED = "skipped"


class GeminiProbeResult(BaseModel):
    """HTTP reachability check for Gemini."""

    domain: str
    status: GeminiProbeStatus
    http_status: int | None = None
    latency_ms: float | None = None
    error: str | None = None


class VpnHealthStatus(str, Enum):
    """Overall health indicator."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class VpnHealthResponse(BaseModel):
    """Aggregate VPN health payload."""

    status: VpnHealthStatus
    interface: InterfaceStatus
    wireguard: WireGuardOverview
    routes: list[RouteEntry]
    probe: GeminiProbeResult
    details: list[str] = Field(default_factory=list)
    source: Literal["vpn-health"] = "vpn-health"
