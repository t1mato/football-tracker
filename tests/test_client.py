"""Tests for the rate-limited football-data.org HTTP client.

No test here touches the network: `responses` intercepts the HTTP layer, and
sleeping is injected so a retry costs microseconds instead of a minute.
"""

from typing import NamedTuple

import pytest
import requests
import responses

from football_pipeline.client import (
    FootballDataClient,
    NotFoundError,
    RateLimitExceeded,
)
from football_pipeline.rate_limiter import RateLimiter

BASE_URL = "https://api.football-data.org/v4"


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeSleep:
    """Records what it was asked to wait for, and moves the clock instead."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        self.clock.advance(seconds)


class Harness(NamedTuple):
    client: FootballDataClient
    sleep: FakeSleep
    clock: FakeClock
    limiter: RateLimiter


def build(**kwargs: object) -> Harness:
    clock = FakeClock()
    sleep = FakeSleep(clock)
    limiter = RateLimiter(capacity=10, per_seconds=60, clock=clock)
    defaults = {"api_token": "test-token", "limiter": limiter, "sleep": sleep}
    client = FootballDataClient(**{**defaults, **kwargs})  # type: ignore[arg-type]
    return Harness(client, sleep, clock, limiter)


@responses.activate
def test_get_returns_the_parsed_envelope_and_authenticates() -> None:
    responses.get(
        f"{BASE_URL}/competitions/PL/standings",
        json={"filters": {}, "standings": [{"position": 1}]},
        status=200,
    )

    data = build().client.get("competitions/PL/standings")

    assert data["standings"] == [{"position": 1}]
    assert responses.calls[0].request.headers["X-Auth-Token"] == "test-token"


@responses.activate
def test_the_limiters_wait_is_slept_before_the_request_goes_out() -> None:
    """The limiter only reports a wait; the client is what actually blocks."""
    responses.get(f"{BASE_URL}/competitions/PL/matches", json={"matches": []}, status=200)

    harness = build()
    for _ in range(10):  # drain the bucket so the next slot costs 6s
        harness.limiter.acquire()

    harness.client.get("competitions/PL/matches")

    assert harness.sleep.calls == [pytest.approx(6.0)]


@responses.activate
def test_the_available_minute_header_corrects_the_bucket_downward() -> None:
    """Our local count is a guess; the server's remaining count is authoritative."""
    responses.get(
        f"{BASE_URL}/competitions/PL/teams",
        json={"teams": []},
        status=200,
        headers={"X-Requests-Available-Minute": "2"},
    )

    harness = build()
    harness.client.get("competitions/PL/teams")

    assert harness.limiter.acquire() == 0.0
    assert harness.limiter.acquire() == 0.0
    assert harness.limiter.acquire() > 0.0


@responses.activate
def test_an_unparseable_available_minute_header_leaves_the_bucket_alone() -> None:
    """A malformed header is no reason to fail a request that already succeeded."""
    responses.get(
        f"{BASE_URL}/competitions/PL/teams",
        json={"teams": []},
        status=200,
        headers={"X-Requests-Available-Minute": "unknown"},
    )

    harness = build()
    data = harness.client.get("competitions/PL/teams")

    assert data == {"teams": []}
    assert harness.limiter.acquire() == 0.0


@responses.activate
def test_a_429_is_retried_after_honouring_retry_after() -> None:
    responses.get(
        f"{BASE_URL}/competitions/PL/matches",
        json={"message": "too many requests"},
        status=429,
        headers={"Retry-After": "30"},
    )
    responses.get(f"{BASE_URL}/competitions/PL/matches", json={"matches": [1]}, status=200)

    harness = build()
    data = harness.client.get("competitions/PL/matches")

    assert data == {"matches": [1]}
    assert harness.sleep.calls == [30.0]
    assert len(responses.calls) == 2


@responses.activate
def test_a_429_without_retry_after_waits_out_a_whole_window() -> None:
    """The probe never saw a Retry-After, so the absent case is the likely one.

    The quota window is a minute, so waiting a full minute is the only wait we
    can justify without guessing.
    """
    responses.get(f"{BASE_URL}/competitions/PL/matches", json={}, status=429)
    responses.get(f"{BASE_URL}/competitions/PL/matches", json={"matches": []}, status=200)

    harness = build()
    harness.client.get("competitions/PL/matches")

    assert harness.sleep.calls == [60.0]


@responses.activate
def test_a_persistent_429_gives_up_rather_than_looping_forever() -> None:
    for _ in range(5):
        responses.get(f"{BASE_URL}/competitions/PL/matches", json={}, status=429)

    harness = build(max_retries=3)

    with pytest.raises(RateLimitExceeded):
        harness.client.get("competitions/PL/matches")

    assert len(responses.calls) == 3


@responses.activate
def test_a_404_raises_rather_than_inventing_an_empty_result() -> None:
    """CL standings 404 before the league phase starts, but so does a typo'd code.

    The client cannot tell those apart, so it refuses to guess: the caller that
    knows which requests may legitimately be empty catches this.
    """
    responses.get(f"{BASE_URL}/competitions/CL/standings", json={}, status=404)

    with pytest.raises(NotFoundError):
        build().client.get("competitions/CL/standings")


@responses.activate
def test_a_server_error_raises_immediately_without_retrying() -> None:
    """Retrying 5xx is unobserved machinery; this test fails if someone adds it."""
    for _ in range(3):
        responses.get(f"{BASE_URL}/competitions/PL/matches", json={}, status=500)

    with pytest.raises(requests.HTTPError):
        build().client.get("competitions/PL/matches")

    assert len(responses.calls) == 1
