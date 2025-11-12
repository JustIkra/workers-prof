"""
VPN diagnostics router (VPN-03).
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.schemas.vpn import VpnHealthResponse, VpnHealthStatus
from app.services.vpn_health import gather_vpn_health

router = APIRouter(prefix="/api/vpn", tags=["VPN"])


@router.get(
    "/health",
    response_model=VpnHealthResponse,
    summary="WireGuard health probe",
    responses={
        status.HTTP_200_OK: {"description": "VPN healthy"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "VPN degraded or disabled"},
    },
)
async def vpn_health() -> Response:
    """
    Return interface state, routes, and Gemini probe results for WireGuard.
    """
    report = await gather_vpn_health()
    status_code = (
        status.HTTP_200_OK
        if report.status is VpnHealthStatus.HEALTHY
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return Response(
        status_code=status_code,
        media_type="application/json",
        content=report.model_dump_json(),
    )
