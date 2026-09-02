"""Token-bucket rate limiter for football-data.org's 10 requests/minute cap.

The limiter never sleeps. `acquire()` reserves a slot and reports how long the
caller must wait before using it, which keeps this module free of side effects
and leaves all blocking to the HTTP client.
"""

from collections.abc import Callable


class RateLimiter:
    """A token bucket holding `capacity` tokens, refilled over `per_seconds`.

    Tokens are allowed to go negative. A negative balance represents slots
    already reserved by earlier callers, so a burst of requests queues up at
    the refill interval rather than all being told to wait the same amount.
    """

    def __init__(
        self,
        capacity: int,
        per_seconds: float,
        clock: Callable[[], float],
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if per_seconds <= 0:
            raise ValueError("per_seconds must be positive")

        self._capacity = float(capacity)
        self._refill_rate = capacity / per_seconds  # tokens per second
        self._clock = clock
        self._tokens = float(capacity)
        self._updated_at = clock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._updated_at
        self._updated_at = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)

    def acquire(self) -> float:
        """Reserve a request slot. Returns seconds the caller must wait."""
        self._refill()
        self._tokens -= 1.0
        if self._tokens >= 0:
            return 0.0
        return -self._tokens / self._refill_rate

    def sync_from_server(self, available: int) -> None:
        """Correct the bucket from the server's own count of remaining requests.

        Only ever downward. The local bucket is an optimistic guess that can
        drift out of step with the server's window; a header claiming *more*
        headroom than we think we have is either stale or counting a window we
        cannot see, and trusting it upward is how you earn a 429.
        """
        self._refill()
        self._tokens = min(self._tokens, float(available))
