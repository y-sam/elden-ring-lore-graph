from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from neo4j import Driver
from neo4j.exceptions import Neo4jError

from elden_lore_api import __version__
from elden_lore_api.config import get_settings
from elden_lore_api.database import create_driver
from elden_lore_api.routers.answers import router as answers_router
from elden_lore_api.routers.claims import router as claims_router
from elden_lore_api.routers.connections import router as connections_router
from elden_lore_api.routers.discovery import router as discovery_router
from elden_lore_api.routers.editorial import router as editorial_router
from elden_lore_api.routers.entities import router as entities_router
from elden_lore_api.routers.feedback import router as feedback_router
from elden_lore_api.routers.search import router as search_router
from elden_lore_api.routers.timeline import router as timeline_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.neo4j_driver = create_driver()
    try:
        yield
    finally:
        app.state.neo4j_driver.close()


def create_app(*, manage_database: bool = True) -> FastAPI:
    request_windows: dict[tuple[str, str], deque[float]] = defaultdict(deque)
    app = FastAPI(
        title="Elden Ring Lore Graph API",
        description="Evidence-first API for lore claims and graph exploration.",
        version=__version__,
        lifespan=lifespan if manage_database else None,
    )
    app.include_router(entities_router, prefix="/api/v1")
    app.include_router(answers_router, prefix="/api/v1")
    app.include_router(claims_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(timeline_router, prefix="/api/v1")
    app.include_router(feedback_router, prefix="/api/v1")
    app.include_router(discovery_router, prefix="/api/v1")
    app.include_router(connections_router, prefix="/api/v1")
    if get_settings().editorial_enabled:
        app.include_router(editorial_router, prefix="/api/v1")

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any):
        settings = get_settings()
        if not settings.editorial_enabled and (
            request.url.path in {"/editorial.html", "/editorial.js"}
            or request.url.path.startswith("/api/v1/editorial")
        ):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        try:
            content_length = int(request.headers.get("content-length", "0") or 0)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
        if content_length > settings.max_request_bytes:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        limits = {
            "/api/v1/answers": settings.answer_rate_limit_per_minute,
            "/api/v1/feedback": settings.feedback_rate_limit_per_minute,
        }
        if request.url.path in limits:
            client = request.client.host if request.client else "unknown"
            key = (client, request.url.path)
            window = request_windows[key]
            now = monotonic()
            while window and window[0] <= now - 60:
                window.popleft()
            if len(window) >= limits[request.url.path]:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
            window.append(now)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; img-src 'self' data:; connect-src 'self'"
        )
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    @app.get("/health", tags=["operations"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/ready", tags=["operations"])
    def ready(request: Request) -> dict[str, str]:
        driver: Driver | None = getattr(request.app.state, "neo4j_driver", None)
        if driver is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Neo4j driver is not initialized",
            )

        settings = get_settings()
        try:
            driver.verify_connectivity()
            with driver.session(database=settings.neo4j_database) as session:
                session.run("RETURN 1 AS ready").consume()
        except (Neo4jError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Neo4j is unavailable",
            ) from exc
        return {"status": "ready"}

    @app.get("/api/v1", tags=["discovery"])
    def api_root() -> dict[str, Any]:
        return {
            "version": "v1",
            "resources": {
                "health": "/health",
                "readiness": "/ready",
                "documentation": "/docs",
                "entities": "/api/v1/entities",
                "claims": "/api/v1/claims/{claim_id}",
                "answers": "/api/v1/answers?q=Who+is+Miquella",
                "search": "/api/v1/search",
                "timeline": "/api/v1/timeline",
                "feedback": "/api/v1/feedback",
                "discovery": "/api/v1/discovery",
                "connections": "/api/v1/connections?from_id={id}&to_id={id}",
                **(
                    {"editorial": "/editorial.html"}
                    if get_settings().editorial_enabled
                    else {}
                ),
            },
        }

    web_directory = Path(__file__).parent / "web"
    app.mount("/", StaticFiles(directory=web_directory, html=True), name="web")

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "elden_lore_api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
