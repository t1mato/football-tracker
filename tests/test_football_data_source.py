"""Tests for the football-data.org dlt source. No test opens a socket."""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import responses

from football_pipeline.client import FootballDataClient, NotFoundError
from football_pipeline.football_data_source import (
    ResponseCache,
    iter_competitions,
    iter_players,
    iter_squad_observations,
    iter_teams,
)
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


def teams_payload(*teams: dict[str, Any]) -> dict[str, Any]:
    return {"count": len(teams), "teams": list(teams)}


ARSENAL = {
    "id": 57, "name": "Arsenal FC", "shortName": "Arsenal", "tla": "ARS",
    "crest": "https://crests.football-data.org/57.png",
    "address": "75 Drayton Park London N5 1BU",
    "website": "http://www.arsenal.com", "founded": 1886,
    "clubColors": "Red / White", "venue": "Emirates Stadium",
    "area": {"id": 2072, "name": "England"},
    "coach": {"id": 11605, "name": "Mikel Arteta", "nationality": "Spain"},
    "runningCompetitions": [{"id": 2021, "code": "PL", "name": "Premier League"}],
    "staff": [],
    "squad": [
        {"id": 3189, "name": "Kepa Arrizabalaga", "position": "Goalkeeper",
         "dateOfBirth": "1994-10-03", "nationality": "Spain"},
        {"id": 3319, "name": "Bukayo Saka", "position": "Offence",
         "dateOfBirth": "2001-09-05", "nationality": "England"},
    ],
    "lastUpdated": "2026-09-02T00:20:34Z",
}


@responses.activate
def test_teams_carries_venue_and_coach_but_not_nested_lists() -> None:
    """runningCompetitions and squad would become dlt child tables keyed on
    _dlt_root_id -- dlt internals leaking into every dbt model downstream.
    """
    for code in ("PL", "CL"):
        responses.get(f"{BASE_URL}/competitions/{code}/teams",
                      json=teams_payload(ARSENAL), status=200)

    rows = list(iter_teams(ResponseCache(make_client()), codes=("PL", "CL")))

    assert rows[0]["venue_name"] == "Emirates Stadium"
    assert rows[0]["coach_name"] == "Mikel Arteta"
    assert "squad" not in rows[0]
    assert "runningCompetitions" not in rows[0]
    assert "staff" not in rows[0]


@responses.activate
def test_teams_in_two_competitions_yield_one_row_per_appearance() -> None:
    """Arsenal is in PL and CL. Merge on id collapses them; the resource does
    not deduplicate, because dlt's merge is what makes that idempotent.
    """
    for code in ("PL", "CL"):
        responses.get(f"{BASE_URL}/competitions/{code}/teams",
                      json=teams_payload(ARSENAL), status=200)

    rows = list(iter_teams(ResponseCache(make_client()), codes=("PL", "CL")))

    assert len(rows) == 2
    assert {r["id"] for r in rows} == {57}


@responses.activate
def test_a_404_outside_standings_propagates_as_an_error() -> None:
    """Only standings may read a 404 as "no data yet". A 404 on teams means a
    bad competition code -- a bug that must fail the run loudly rather than
    silently producing an empty table.
    """
    responses.get(f"{BASE_URL}/competitions/XX/teams", json={}, status=404)

    with pytest.raises(NotFoundError):
        list(iter_teams(ResponseCache(make_client()), codes=("XX",)))


@responses.activate
def test_players_carry_the_team_id_of_the_squad_that_embedded_them() -> None:
    """The squad payload has no team_id; without injecting it here, dbt would
    have to recover the link from dlt's _dlt_root_id.
    """
    responses.get(f"{BASE_URL}/competitions/PL/teams",
                  json=teams_payload(ARSENAL), status=200)

    rows = list(iter_players(ResponseCache(make_client()), codes=("PL",)))

    assert {r["team_id"] for r in rows} == {57}
    assert {r["id"] for r in rows} == {3189, 3319}
    assert rows[0]["position"] == "Goalkeeper"
    assert rows[0]["date_of_birth"] == "1994-10-03"


@responses.activate
def test_squad_observations_are_stamped_with_the_given_utc_date() -> None:
    """observed_date is injected, never read from the clock in here, so the
    UTC rule is testable rather than a matter of trust.
    """
    responses.get(f"{BASE_URL}/competitions/PL/teams",
                  json=teams_payload(ARSENAL), status=200)

    rows = list(iter_squad_observations(
        ResponseCache(make_client()), observed_on=date(2026, 9, 3), codes=("PL",)
    ))

    assert len(rows) == 2
    assert {r["observed_date"] for r in rows} == {"2026-09-03"}
    assert {(r["team_id"], r["player_id"]) for r in rows} == {(57, 3189), (57, 3319)}


@responses.activate
def test_players_and_observations_share_one_teams_request() -> None:
    """Both read the same payload; the run budget assumes one request."""
    responses.get(f"{BASE_URL}/competitions/PL/teams",
                  json=teams_payload(ARSENAL), status=200)
    cache = ResponseCache(make_client())

    list(iter_players(cache, codes=("PL",)))
    list(iter_squad_observations(cache, observed_on=date(2026, 9, 3), codes=("PL",)))
    list(iter_teams(cache, codes=("PL",)))

    assert len(responses.calls) == 1
