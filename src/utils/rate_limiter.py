"""Simple async rate limiter with jitter."""

import asyncio
import random
import time
from collections import deque

from src.config.settings import settings
from src.utils.logger import logger


class RateLimiter:
    """Token-style limiter using rolling 60 second windows."""

    def __init__(
        self,
        requests_per_minute: int = settings.RATE_LIMIT_REQUESTS,
        min_delay: float = settings.MIN_REQUEST_DELAY,
        max_delay: float = settings.MAX_REQUEST_DELAY,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_times: deque[float] = deque(maxlen=requests_per_minute)
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until making another request is safe."""
        async with self.lock:
            now = time.time()
            cutoff = now - 60
            while self.request_times and self.request_times[0] < cutoff:
                self.request_times.popleft()

            if len(self.request_times) >= self.requests_per_minute:
                wait_time = 60 - (now - self.request_times[0])
                if wait_time > 0:
                    logger.warning("Rate limit reached. Sleeping %.2fs", wait_time)
                    await asyncio.sleep(wait_time)

            await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))
            self.request_times.append(time.time())

    def reset(self) -> None:
        self.request_times.clear()
        logger.info("Rate limiter reset")


rate_limiter = RateLimiter()
