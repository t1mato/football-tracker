"""Tests for the token-bucket limiter guarding football-data.org's 10 req/min."""

import pytest

from football_pipeline.rate_limiter import RateLimiter


class FakeClock:
    """A clock we control, so tests never actually sleep."""

    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_a_full_bucket_allows_capacity_requests_without_waiting() -> None:
    limiter = RateLimiter(capacity=10, per_seconds=60, clock=FakeClock())

    waits = [limiter.acquire() for _ in range(10)]

    assert waits == [0.0] * 10


def test_the_request_after_a_drained_bucket_waits_for_one_refill() -> None:
    limiter = RateLimiter(capacity=10, per_seconds=60, clock=FakeClock())
    for _ in range(10):
        limiter.acquire()

    # 10 tokens per 60s means one token every 6s.
    assert limiter.acquire() == pytest.approx(6.0)


def test_waiting_refills_the_bucket() -> None:
    clock = FakeClock()
    limiter = RateLimiter(capacity=10, per_seconds=60, clock=clock)
    for _ in range(10):
        limiter.acquire()

    clock.advance(6.0)

    assert limiter.acquire() == 0.0


def test_an_idle_bucket_never_refills_past_capacity() -> None:
    clock = FakeClock()
    limiter = RateLimiter(capacity=10, per_seconds=60, clock=clock)

    clock.advance(3600.0)  # an hour idle must not bank 600 requests

    waits = [limiter.acquire() for _ in range(10)]
    assert waits == [0.0] * 10
    assert limiter.acquire() == pytest.approx(6.0)


def test_a_burst_past_capacity_queues_at_the_refill_interval() -> None:
    limiter = RateLimiter(capacity=10, per_seconds=60, clock=FakeClock())
    for _ in range(10):
        limiter.acquire()

    # Each caller in a burst gets its own slot, not the same one.
    assert limiter.acquire() == pytest.approx(6.0)
    assert limiter.acquire() == pytest.approx(12.0)
    assert limiter.acquire() == pytest.approx(18.0)


def test_server_header_lowers_an_optimistic_bucket() -> None:
    """X-Requests-Available-Minute is the truth; our local count is a guess."""
    limiter = RateLimiter(capacity=10, per_seconds=60, clock=FakeClock())

    limiter.sync_from_server(available=3)

    waits = [limiter.acquire() for _ in range(3)]
    assert waits == [0.0] * 3
    assert limiter.acquire() > 0.0


def test_server_header_never_raises_the_bucket_above_our_own_count() -> None:
    """A stale or generous header must not licence a burst we can't afford."""
    clock = FakeClock()
    limiter = RateLimiter(capacity=10, per_seconds=60, clock=clock)
    for _ in range(10):
        limiter.acquire()

    limiter.sync_from_server(available=8)

    assert limiter.acquire() > 0.0
