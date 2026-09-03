"""Tests for the football-data.org dlt source. No test opens a socket."""

from pathlib import Path

import pytest
import responses

from football_pipeline.client import FootballDataClient, NotFoundError
from football_pipeline.football_data_source import ResponseCache
from football_pipeline.rate_limiter import RateLimiter

BASE_URL = "https://api.football-data.org/v4"
FIXTURES = Path(__file__).parent / "fixtures"


def make_client() -> FootballDataClient:
    """A client whose limiter never makes a test wait."""
    return FootballDataClient(
        api_token="test-token",
        limiter=RateLimiter(capacity=10, per_seconds=60, clock=lambda: 0.0),
        sleep=lambda seconds: None,
    )


@responses.activate
def test_the_cache_fetches_each_url_once_however_many_resources_ask() -> None:
    """teams, players and squad_observations all read one teams payload.

    dlt does not guarantee resource order, so correctness cannot depend on
    which resource asks first -- only that the request happens once.
    """
    responses.get(f"{BASE_URL}/competitions/PL/teams", json={"teams": []}, status=200)

    cache = ResponseCache(make_client())
    first = cache.get("competitions/PL/teams")
    second = cache.get("competitions/PL/teams")

    assert first is second
    assert len(responses.calls) == 1


@responses.activate
def test_a_404_is_remembered_so_the_same_dead_url_is_not_refetched() -> None:
    """CL standings 404 all summer, and two resources both ask for them.

    Only NotFoundError is cached: a 404 is a fact about the URL, while a
    timeout or a 500 is transient and must be retried.
    """
    responses.get(f"{BASE_URL}/competitions/CL/standings", json={}, status=404)

    cache = ResponseCache(make_client())

    with pytest.raises(NotFoundError):
        cache.get("competitions/CL/standings")
    with pytest.raises(NotFoundError):
        cache.get("competitions/CL/standings")

    assert len(responses.calls) == 1
