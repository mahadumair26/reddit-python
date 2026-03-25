"""Base scraper class with request, retry, and cache support."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.scrapers.user_agent import pick_user_agent
from src.utils.cache import cache
from src.utils.rate_limiter import rate_limiter


class BaseScraper(ABC):
    """Shared functionality for concrete scraper classes."""

    def __init__(self) -> None:
        self.base_url = settings.REDDIT_BASE_URL
        self.timeout = settings.REQUEST_TIMEOUT
        self.max_retries = settings.MAX_RETRIES
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        self.client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()

    async def _request(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
    ) -> str:
        """Fetch URL with retries, jitter limiter, and optional cache."""
        if not self.client:
            await self.connect()
        assert self.client is not None

        cache_key = f"scraper:{url}:{params}"
        if use_cache:
            cached = await cache.get(cache_key)
            if isinstance(cached, str):
                return cached

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
            reraise=True,
        ):
            with attempt:
                await rate_limiter.acquire()
                response = await self.client.get(
                    url,
                    params=params,
                    headers={
                        "User-Agent": pick_user_agent(),
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.8",
                    },
                )
                response.raise_for_status()
                payload = response.text
                if use_cache and response.status_code == 200:
                    await cache.set(cache_key, payload, ttl=cache_ttl)
                return payload

        return ""

    async def _request_json(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
    ) -> dict[str, Any]:
        """Fetch JSON URL with retries, jitter limiter, and optional cache."""
        if not self.client:
            await self.connect()
        assert self.client is not None

        cache_key = f"scraper_json:{url}:{params}"
        if use_cache:
            cached = await cache.get(cache_key)
            if isinstance(cached, dict):
                return cached

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException, ValueError)),
            reraise=True,
        ):
            with attempt:
                await rate_limiter.acquire()
                response = await self.client.get(
                    url,
                    params=params,
                    headers={
                        "User-Agent": pick_user_agent(),
                        "Accept": "application/json,text/plain;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.8",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if use_cache and response.status_code == 200:
                    await cache.set(cache_key, payload, ttl=cache_ttl)
                return payload

        return {}

    @staticmethod
    def _parse_html(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urljoin(self.base_url, path)

    @abstractmethod
    async def scrape(self, *args, **kwargs) -> Any:
        """Required scrape method for subclasses."""
