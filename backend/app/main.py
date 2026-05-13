"""FastAPI application factory for FPA Copilot."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import forecast, health


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(title="FP&A Copilot", version="0.1.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix="/api/v1")
    application.include_router(forecast.router, prefix="/api/v1")

    return application


app = create_app()
