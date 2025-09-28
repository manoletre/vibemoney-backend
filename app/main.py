from fastapi import FastAPI

from app.core.config import settings
from app.api.v1.routers.timeseries import router as timeseries_router
from app.api.v1.routers.quarterly import router as quarterly_router
from app.api.v1.routers.latestevents import router as latestevents_router
from app.api.v1.routers.sentiment import router as sentiment_router
from app.api.v1.routers.chat import router as chat_router
from app.api.v1.routers.estimates import router as estimates_router
from app.api.v1.routers.profit import router as profit_router


def create_app() -> FastAPI:
    """
    Application factory to create the FastAPI app instance.

    Returns
    -------
    FastAPI
        Configured FastAPI application with versioned API routes included.
    """

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    # Health and metadata endpoints
    @app.get("/", tags=["meta"], summary="Service metadata")
    def read_root() -> dict:
        return {
            "name": settings.app_name,
            "version": settings.version,
            "api_prefix": settings.api_prefix,
            "status": "ok",
        }

    @app.get("/health", tags=["meta"], summary="Health check")
    def health() -> dict:
        return {"status": "healthy"}

    # Versioned API routers
    app.include_router(timeseries_router, prefix=settings.api_prefix)
    app.include_router(quarterly_router, prefix=settings.api_prefix)
    app.include_router(latestevents_router, prefix=settings.api_prefix)
    app.include_router(sentiment_router, prefix=settings.api_prefix)
    app.include_router(chat_router, prefix=settings.api_prefix)
    app.include_router(estimates_router, prefix=settings.api_prefix)
    app.include_router(profit_router, prefix=settings.api_prefix)

    return app


app = create_app()


