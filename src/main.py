"""FastAPI app entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencies import scraper
from src.api.middleware import register_middleware
from src.api.routes import router
from src.config.settings import settings
from src.utils.cache import cache
from src.utils.logger import logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize and close external resources."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    await cache.connect()
    await scraper.connect()
    yield
    await scraper.disconnect()
    await cache.disconnect()
    logger.info("Service shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_middleware(app)
app.include_router(router, prefix=settings.API_PREFIX, tags=["reddit-scraper"])
