"""Tests for the football-data.org dlt source. No test opens a socket."""

from pathlib import Path

import pytest
import responses

from football_pipeline.client import FootballDataClient, NotFoundError
from football_pipeline.football_data_source import ResponseCache, iter_competitions
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


COMPETITIONS_PAYLOAD = {
    "count": 3,
    "competitions": [
        {
            "id": 2021, "code": "PL", "name": "Premier League", "type": "LEAGUE",
            "area": {"id": 2072, "name": "England"},
            "currentSeason": {
                "id": 2502, "startDate": "2026-08-21", "endDate": "2027-05-30",
                "currentMatchday": 3, "winner": None,
            },
            "numberOfAvailableSeasons": 128,
        },
        {
            "id": 2001, "code": "CL", "name": "UEFA Champions League", "type": "CUP",
            "area": {"id": 2077, "name": "Europe"},
            "currentSeason": {
                "id": 2557, "startDate": "2026-09-08", "endDate": "2027-01-27",
                "currentMatchday": 1, "winner": None,
            },
            "numberOfAvailableSeasons": 47,
        },
        {
            "id": 2013, "code": "BSA", "name": "Serie A Brazil", "type": "LEAGUE",
            "area": {"id": 2032, "name": "Brazil"},
            "currentSeason": {
                "id": 2000, "startDate": "2026-01-01", "endDate": "2026-12-01",
                "currentMatchday": 1, "winner": None,
            },
            "numberOfAvailableSeasons": 10,
        },
    ],
}


@responses.activate
def test_competitions_keeps_only_the_six_we_track() -> None:
    """The endpoint returns all 13 free-tier competitions; we want six."""
    responses.get(f"{BASE_URL}/competitions", json=COMPETITIONS_PAYLOAD, status=200)

    rows = list(iter_competitions(ResponseCache(make_client())))

    assert [r["code"] for r in rows] == ["PL", "CL"]
    assert rows[0]["id"] == 2021
    assert rows[0]["area_name"] == "England"


@responses.activate
def test_competitions_does_not_carry_number_of_available_seasons() -> None:
    """It advertises total history (PL claims 128), not free-tier access.

    Keeping it invites someone to build a backfill loop on it that would fire
    hundreds of requests returning 403.
    """
    responses.get(f"{BASE_URL}/competitions", json=COMPETITIONS_PAYLOAD, status=200)

    rows = list(iter_competitions(ResponseCache(make_client())))

    assert "numberOfAvailableSeasons" not in rows[0]
    assert "number_of_available_seasons" not in rows[0]
