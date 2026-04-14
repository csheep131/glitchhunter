"""
FastAPI server for GlitchHunter.

Creates and configures the FastAPI application with middleware,
CORS, lifespan handlers, and route registration.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..core.config import Config
from ..core.logging_config import setup_logging
from .routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("GlitchHunter API starting up...")

    try:
        # Load configuration
        config = Config.load()
        app.state.config = config

        # Setup logging based on config
        setup_logging(config.logging)

        logger.info("Configuration loaded successfully")

    except Exception as e:
        logger.error(f"Startup error: {e}")
        # Continue anyway with defaults

    yield

    # Shutdown
    logger.info("GlitchHunter API shutting down...")

    # TODO: Cleanup resources
    # - Close database connections
    # - Shutdown MCP client
    # - Unload models


def create_app(config_path: str | None = None) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="GlitchHunter API",
        description="AI-powered autonomous code analysis and bug-fixing system",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router, prefix="/api")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.error(f"Uncaught exception: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {"type": type(exc).__name__},
            },
        )

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root() -> dict:
        """Root endpoint with API information."""
        return {
            "name": "GlitchHunter API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


def main() -> None:
    """
    Main entry point for running the API server.

    Can be called directly or via uvicorn.
    """
    import uvicorn

    # Load configuration
    try:
        config = Config.load()
        setup_logging(config.logging)
    except Exception as e:
        # Setup basic logging if config fails
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load config: {e}, using defaults")
        config = None

    # Get host and port from config or use defaults
    host = "0.0.0.0"
    port = 8000
    reload = False

    if config:
        host = config.api.host
        port = config.api.port
        reload = config.api.debug

    logger.info(f"Starting GlitchHunter API on {host}:{port}")

    uvicorn.run(
        "src.api.server:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
