"""HTTP client for football-data.org v4, rate-limited and side-effect honest."""

import contextlib
import time
from collections.abc import Callable, Mapping
from typing import Any

import requests

from football_pipeline.rate_limiter import RateLimiter

BASE_URL = "https://api.football-data.org/v4"

# The quota window is a minute, so a 429 with no Retry-After costs us a window.
DEFAULT_RETRY_AFTER = 60.0


class FootballDataError(Exception):
    """Base for every error this client raises deliberately."""


class NotFoundError(FootballDataError):
    """A 404. Means "no data yet" for some endpoints and "wrong URL" for others.

    Only the caller knows which, so the client refuses to decide.
    """


class RateLimitExceeded(FootballDataError):
    """The server kept returning 429 after we exhausted our retries."""


class FootballDataClient:
    def __init__(
        self,
        api_token: str,
        limiter: RateLimiter,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        base_url: str = BASE_URL,
        max_retries: int = 3,
        timeout: float = 30.0,
    ) -> None:
        self._limiter = limiter
        self._sleep = sleep
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update({"X-Auth-Token": api_token})

    def get(self, path: str, params: Mapping[str, str | int] | None = None) -> dict[str, Any]:
        url = f"{self._base_url}/{path.lstrip('/')}"
        for _ in range(self._max_retries):
            wait = self._limiter.acquire()
            if wait > 0:
                self._sleep(wait)

            response = self._session.get(url, params=params, timeout=self._timeout)
            self._sync_limiter(response)

            if response.status_code == 429:
                # The server has just told us the window is spent.
                self._limiter.sync_from_server(0)
                self._sleep(_retry_after(response))
                continue

            if response.status_code == 404:
                raise NotFoundError(url)

            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data

        raise RateLimitExceeded(f"still rate limited after {self._max_retries} attempts: {url}")

    def _sync_limiter(self, response: requests.Response) -> None:
        available = response.headers.get("X-Requests-Available-Minute")
        if available is None:
            return
        # A malformed header is no reason to fail a response that succeeded.
        with contextlib.suppress(ValueError):
            self._limiter.sync_from_server(int(available))


def _retry_after(response: requests.Response) -> float:
    """Seconds to wait after a 429, falling back to a full quota window."""
    raw = response.headers.get("Retry-After")
    if raw is None:
        return DEFAULT_RETRY_AFTER
    try:
        return float(int(raw))
    except ValueError:
        # The spec also permits an HTTP-date here, which we have never seen.
        return DEFAULT_RETRY_AFTER
