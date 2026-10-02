"""FastAPI application factory for the agentcore multi-agent system.

Creates and configures the FastAPI app with all v2 routes. The app can be
run standalone (``uvicorn agentcore.api.app:create_app --factory``) or
imported by a parent app that mounts it under a prefix.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Startup: nothing heavy here — agents/LLM/Pinecone are lazy-init.
    # Could warm up connections if needed in production.
    yield
    # Shutdown: cleanup would go here (close LLM client, Pinecone, Redis)


def _cors_origins() -> list[str]:
    """Build allowed origins list from environment.

    FRONTEND_URL  — the Vercel production/preview URL (required in prod).
    Localhost dev origins are always included so local development works
    without setting FRONTEND_URL.
    """
    origins = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://localhost:3000",
    ]
    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if frontend_url and frontend_url not in origins:
        origins.append(frontend_url)
    return origins


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="ClaimBlitz Multi-Agent API",
        version="2.0.0",
        description=(
            "Enterprise-grade collaborative multi-agent system for "
            "medical insurance claim processing."
        ),
        lifespan=lifespan,
    )

    # CORS — production-safe: explicit frontend origins, not "*"
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/v2")
    # Also mount /process at root for frontend compatibility
    app.include_router(router, prefix="")
    return app


# Module-level instance for ``uvicorn main:app`` / ``uvicorn agentcore.api.app:app``
app = create_app()
