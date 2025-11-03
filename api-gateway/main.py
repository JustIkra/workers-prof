"""
Main FastAPI application entry point.

Single application on port 9187 (HTTP), served behind Nginx Proxy Manager (TLS/HTTPS).
Loads configuration from ROOT .env file.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, validate_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    print("="* 60)
    print("🚀 Starting Workers Proficiency Assessment System")
    print("=" * 60)

    # Validate configuration
    validate_config()

    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Initialize Celery client

    print("=" * 60)
    print(f"✓ Application ready on port {settings.app_port}")
    print("=" * 60)

    yield

    # Shutdown
    print("\n" + "=" * 60)
    print("🛑 Shutting down application")
    print("=" * 60)

    # TODO: Close database connections
    # TODO: Close Redis connections
    # TODO: Close Celery connections

    print("✓ Shutdown complete")


# ===== Create FastAPI Application =====
app = FastAPI(
    title="Workers Proficiency Assessment API",
    description=(
        "Professional competency assessment system. "
        "Extracts metrics from reports, calculates fitness scores, "
        "and generates personalized recommendations."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    root_path=settings.app_root_path,
    lifespan=lifespan,
)


# ===== CORS Middleware =====
if settings.cors_allow_all or settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ===== Health Check Endpoint =====
@app.get("/api/healthz", tags=["Health"])
async def healthz():
    """
    Health check endpoint.

    Returns 200 OK if the application is running.
    Used by NPM and monitoring systems.
    """
    return {
        "status": "ok",
        "service": "api-gateway",
        "version": "0.1.0",
        "env": settings.env,
    }


# ===== Root Endpoint =====
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.

    Provides basic API information.
    """
    return {
        "message": "Workers Proficiency Assessment API",
        "version": "0.1.0",
        "docs": "/api/docs",
        "health": "/api/healthz",
    }


# ===== TODO: Register Routers =====
# from app.routers import auth, participants, reports, metrics, weights, scoring, admin
# app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
# app.include_router(participants.router, prefix="/api/participants", tags=["Participants"])
# app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
# app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
# app.include_router(weights.router, prefix="/api/weights", tags=["Weights"])
# app.include_router(scoring.router, prefix="/api/scoring", tags=["Scoring"])
# app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.is_dev,
        proxy_headers=settings.uvicorn_proxy_headers,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        log_level=settings.log_level.lower(),
    )
