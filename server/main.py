"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server.config import load_config
from server.middleware.security import SecurityHeadersMiddleware
from server.middleware.rate_limit import cleanup_expired as cleanup_rate_limits
from server.routes.api import router as api_router
from server.routes.auth import router as auth_router
from server.routes.sub import router as sub_router
from server.utils.session import cleanup_expired as cleanup_sessions
from server.utils.store import cleanup_expired as cleanup_subs, init_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle manager."""
    config = load_config()
    app.state.config = config
    init_store(config.subscription.storage_path)
    logger.info(
        "Server starting on %s:%d (base_url=%s)",
        config.server.host,
        config.server.port,
        config.server.base_url,
    )

    async def periodic_cleanup() -> None:
        while True:
            await asyncio.sleep(600)
            s = cleanup_sessions()
            r = cleanup_rate_limits()
            f = cleanup_subs(config.subscription.storage_path)
            if s or r or f:
                logger.info(
                    "Cleanup: %d sessions, %d rate limits, %d subs",
                    s, r, f,
                )

    task = asyncio.create_task(periodic_cleanup())

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Server shut down cleanly")


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(SecurityHeadersMiddleware)

app.mount("/optimize", StaticFiles(directory="public", html=True), name="optimize")

app.include_router(auth_router, prefix="/api/auth")
app.include_router(api_router, prefix="/api")
app.include_router(sub_router, prefix="/sub")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "ok"}
