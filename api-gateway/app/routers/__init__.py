"""
API routers.
"""

from app.routers import admin, auth, participants, prof_activities, reports, vpn, weights

__all__ = [
    "auth",
    "admin",
    "participants",
    "prof_activities",
    "reports",
    "weights",
    "vpn",
]
